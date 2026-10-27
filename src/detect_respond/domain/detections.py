"""A detection is a rule written as data: an event pattern, a severity and the responder's first step."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from detect_respond.domain.errors import InvalidDetectionError
from detect_respond.domain.events import AuditEvent
from detect_respond.domain.pattern import matches

SEVERITIES = ("low", "medium", "high", "critical")
DEPLOY_TARGETS = {"global", "home", "watch"}


@dataclass(frozen=True)
class Detection:
    """One detection. `deploy_to` names where the rule runs: `global` (the Region that receives global service events),
    `home` (the Region the account works in) and `watch` (each Region the account does not operate in)."""

    detection_id: str
    title: str
    severity: str
    description: str
    first_step: str
    prevention: str
    deploy_to: tuple[str, ...]
    pattern: Mapping[str, Any]
    parameters: tuple[str, ...] = ()
    parameter_variables: Mapping[str, str] = field(default_factory=dict)
    include_read_only: bool = False

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> Detection:
        """Validate and build from the JSON form."""
        try:
            detection = cls(
                detection_id=raw["id"],
                title=raw["title"],
                severity=raw["severity"],
                description=raw["description"],
                first_step=raw["firstStep"],
                prevention=raw["prevention"],
                deploy_to=tuple(raw["deployTo"]),
                pattern=raw["pattern"],
                parameters=tuple(raw.get("parameters", ())),
                parameter_variables=raw.get("parameterVariables", {}),
                include_read_only=bool(raw.get("includeReadOnly", False)),
            )
        except KeyError as error:
            raise InvalidDetectionError(f"detection lacks the field {error}") from error
        if detection.severity not in SEVERITIES:
            raise InvalidDetectionError(f"{detection.detection_id}: severity must be one of {SEVERITIES}")
        unknown = set(detection.deploy_to) - DEPLOY_TARGETS
        if unknown or not detection.deploy_to:
            raise InvalidDetectionError(f"{detection.detection_id}: deployTo must name {sorted(DEPLOY_TARGETS)}")
        return detection

    def with_parameters(self, values: Mapping[str, str]) -> Detection:
        """The detection with its placeholders replaced, for example the honeytoken's access key id."""
        text = json.dumps(self.pattern)
        for placeholder, value in values.items():
            text = text.replace(placeholder, value)
        remaining = tuple(p for p in self.parameters if p not in values)
        return replace(self, pattern=json.loads(text), parameters=remaining)

    @property
    def complete(self) -> bool:
        """False while a placeholder is unresolved; such a detection never fires."""
        return not self.parameters

    def fires(self, event: AuditEvent) -> bool:
        """True when the event matches the pattern. Failed calls match too: an attempt is as telling as a success."""
        return self.complete and matches(self.pattern, event.envelope())
