"""Checks that the rules in a plan are the detections in `detections/`: the tested pattern is the deployed one."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from detect_respond.domain.detections import Detection
from detect_respond.domain.errors import PlanError

ALL_EVENTS_STATE = "ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS"
_MODULE_PREFIX = {"global": "module.alerting_global", "home": "module.alerting_home", "watch": "module.alerting_watch"}


@dataclass(frozen=True)
class PlannedRule:
    """A rule as the plan would create it."""

    module: str
    name: str
    state: str
    pattern: Mapping[str, Any]


def planned_rules(plan: Mapping[str, Any]) -> tuple[PlannedRule, ...]:
    """The event rules that exist after the plan."""
    rules = []
    for change in plan.get("resource_changes", []):
        after = change["change"].get("after")
        if change["type"] == "aws_cloudwatch_event_rule" and after is not None:
            rules.append(
                PlannedRule(
                    change.get("module_address", ""),
                    after["name"],
                    after.get("state", "ENABLED"),
                    json.loads(after["event_pattern"]),
                )
            )
    return tuple(rules)


def audit_rules(plan_path: Path, detections: Sequence[Detection]) -> list[str]:
    """Problems found: a detection with no rule where it should be deployed, a rule whose pattern differs from the
    detection's, or a rule that would miss read-only calls. Empty when the plan deploys exactly the detections."""
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    variables = {name: spec.get("value") for name, spec in plan.get("variables", {}).items()}
    rules = planned_rules(plan)
    if not rules:
        raise PlanError("the plan creates no event rules")
    problems = []
    for detection in detections:
        values = {p: str(variables.get(detection.parameter_variables.get(p, ""), "")) for p in detection.parameters}
        if detection.parameters and not all(values.values()):
            continue  # a parameterized detection is deployed only when its variable is set
        expected = detection.with_parameters(values).pattern
        for target in detection.deploy_to:
            where = [r for r in rules if r.module.startswith(_MODULE_PREFIX[target])]
            deployed = [r for r in where if r.name.endswith(f"-{detection.detection_id.lower()}")]
            if not deployed:
                problems.append(f"{detection.detection_id} is not deployed to {target}")
            for rule in deployed:
                if rule.pattern != expected:
                    problems.append(f"{detection.detection_id} in {rule.module} differs from detections/")
                if detection.include_read_only and rule.state != ALL_EVENTS_STATE:
                    problems.append(
                        f"{detection.detection_id} must use the rule state that includes read-only management events"
                    )
    return problems
