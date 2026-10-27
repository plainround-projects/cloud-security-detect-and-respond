"""The lesson's use cases: detect, rebuild the timeline, measure, contain, verify the archive, baseline the posture."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from detect_respond.application.ports import Clock, DetectionCatalog, LogArchive, PostureSource, Revoker
from detect_respond.domain.alerts import render_alert
from detect_respond.domain.containment import RevocationPlan, plan_revocation
from detect_respond.domain.detections import Detection
from detect_respond.domain.digest import DigestResult, verify_digest
from detect_respond.domain.drill import DrillMeasure, measure
from detect_respond.domain.events import AuditEvent
from detect_respond.domain.posture import Baseline, baseline
from detect_respond.domain.timeline import TimelineEntry, build_timeline


@dataclass(frozen=True)
class Alert:
    """A detection that fired on an event, with the text the responder would receive."""

    detection: Detection
    event: AuditEvent
    text: str


def resolved_detections(catalog: DetectionCatalog, parameters: Mapping[str, str]) -> tuple[Detection, ...]:
    """The catalog's detections with their placeholders filled in where a value is given."""
    return tuple(
        d.with_parameters({k: v for k, v in parameters.items() if k in d.parameters}) for d in catalog.detections()
    )


def scan_logs(archive: LogArchive, catalog: DetectionCatalog, parameters: Mapping[str, str]) -> tuple[Alert, ...]:
    """Run every detection over every event in the archive, oldest event first.

    This is the batch twin of the rules in the account, and it also sees what a rule in one Region cannot: all Regions.
    """
    template = catalog.template()
    rules = resolved_detections(catalog, parameters)
    alerts = []
    for event in sorted(archive.events(), key=lambda candidate: candidate.time):
        alerts += [Alert(rule, event, render_alert(template, rule, event)) for rule in rules if rule.fires(event)]
    return tuple(alerts)


@dataclass(frozen=True)
class Drill:
    """The rebuilt timeline and the measured times."""

    timeline: tuple[TimelineEntry, ...]
    measured: DrillMeasure


def run_drill(
    archive: LogArchive,
    catalog: DetectionCatalog,
    role_name: str,
    session: str,
    user_name: str,
    alert_times: Mapping[str, datetime],
) -> Drill:
    """Rebuild what the session did from the archive alone, then measure time to detect and time to contain."""
    rules = resolved_detections(catalog, {})
    timeline = build_timeline(archive.events(), rules, role_name, session, user_name)
    return Drill(timeline, measure(timeline, alert_times))


@dataclass(frozen=True)
class Containment:
    """What containment decided and whether it was applied."""

    plan: RevocationPlan
    applied: bool


def contain(
    revoker: Revoker,
    clock: Clock,
    role_name: str,
    user_name: str,
    access_key_ids: tuple[str, ...],
    *,
    apply: bool,
) -> Containment:
    """Revoke the role's sessions issued before now and deactivate the user's keys. Without `apply`, only plan."""
    keys = access_key_ids or revoker.list_access_keys(user_name)
    plan = plan_revocation(role_name, user_name, keys, clock.now())
    if apply:
        revoker.put_role_policy(role_name, plan.policy_name, plan.policy)
        for key in plan.access_key_ids:
            revoker.deactivate_access_key(user_name, key)
    return Containment(plan, apply)


def verify_archive(archive: LogArchive) -> tuple[DigestResult, ...]:
    """Check every digest in the archive against the log files it lists."""
    return tuple(verify_digest(digest, archive.read_log) for digest in archive.digests())


def posture_baseline(source: PostureSource, before: str, after: str) -> Baseline:
    """The baseline from two findings files and the accepted risks."""
    return baseline(source.findings(before), source.findings(after), source.acceptances())
