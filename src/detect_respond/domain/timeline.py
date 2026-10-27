"""Rebuild what a credential did from the audit log alone: the attacker's calls (denied too) and the responder's."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from detect_respond.domain.detections import Detection
from detect_respond.domain.events import AuditEvent

CONTAINMENT_CALLS = frozenset({"PutRolePolicy", "UpdateAccessKey", "DeleteAccessKey", "DeleteRolePolicy"})


@dataclass(frozen=True)
class TimelineEntry:
    """One line of the timeline: the event, who made it, and the detections it raises."""

    event: AuditEvent
    actor: str
    detections: tuple[str, ...]


def _is_attacker(event: AuditEvent, role_name: str, session: str) -> bool:
    if event.session_of(role_name) == session:
        return True
    assumed = event.name == "AssumeRole" and str(event.request.get("roleArn", "")).endswith(f":role/{role_name}")
    return assumed and event.request.get("roleSessionName") == session


def _is_responder(event: AuditEvent, role_name: str, user_name: str) -> bool:
    if event.name not in CONTAINMENT_CALLS:
        return False
    return event.request.get("roleName") == role_name or event.request.get("userName") == user_name


def build_timeline(
    events: Iterable[AuditEvent],
    detections: Iterable[Detection],
    role_name: str,
    session: str,
    user_name: str,
) -> tuple[TimelineEntry, ...]:
    """The session's calls and the responder's containment calls, oldest first, each with the detections it raises."""
    rules = tuple(detections)
    entries = []
    for event in sorted(events, key=lambda candidate: candidate.time):
        if _is_attacker(event, role_name, session):
            actor = "attacker"
        elif _is_responder(event, role_name, user_name):
            actor = "responder"
        else:
            continue
        entries.append(TimelineEntry(event, actor, tuple(rule.detection_id for rule in rules if rule.fires(event))))
    return tuple(entries)
