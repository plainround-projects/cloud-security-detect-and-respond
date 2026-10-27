"""The two numbers the lesson asks for: time to detect and time to contain, measured from the first attacker action."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

from detect_respond.domain.errors import DrillError
from detect_respond.domain.timeline import TimelineEntry


@dataclass(frozen=True)
class DrillMeasure:
    """Measured times. `contained_at` is the first call refused after the revocation (None if none was tried)."""

    first_action: datetime
    first_alert: datetime | None
    revoked_at: datetime | None
    contained_at: datetime | None
    detections: tuple[str, ...]

    @property
    def time_to_detect(self) -> timedelta | None:
        """First attacker action to the first alert."""
        return None if self.first_alert is None else self.first_alert - self.first_action

    @property
    def time_to_contain(self) -> timedelta | None:
        """First attacker action to the first call that revocation refused."""
        return None if self.contained_at is None else self.contained_at - self.first_action


def format_duration(span: timedelta | None) -> str:
    """Seconds under a minute, otherwise minutes and seconds: `32 s`, `6 min 52 s`."""
    if span is None:
        return "not measured"
    total = int(span.total_seconds())
    minutes, seconds = divmod(total, 60)
    return f"{seconds} s" if minutes == 0 else f"{minutes} min {seconds} s"


def measure(timeline: tuple[TimelineEntry, ...], alert_times: Mapping[str, datetime]) -> DrillMeasure:
    """Measure the drill. `alert_times` maps an event id to when its alert reached the responder; an event without an
    entry is taken to alert at the moment it happened, which is the lower bound."""
    attacker = [entry for entry in timeline if entry.actor == "attacker"]
    if not attacker:
        raise DrillError("the events contain no call by the attacker's session")
    first_action = attacker[0].event.time
    alerts = [alert_times.get(e.event.event_id, e.event.time) for e in attacker if e.detections]
    revocations = [entry for entry in timeline if entry.actor == "responder" and entry.event.name == "PutRolePolicy"]
    revoked_at = revocations[0].event.time if revocations else None
    refused = [
        entry.event.time
        for entry in attacker
        if revoked_at is not None and entry.event.time > revoked_at and entry.event.denied
    ]
    fired = tuple(dict.fromkeys(rule for entry in attacker for rule in entry.detections))
    return DrillMeasure(
        first_action, min(alerts) if alerts else None, revoked_at, min(refused) if refused else None, fired
    )
