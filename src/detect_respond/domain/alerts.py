"""The text of an alert, built from the detection and the event."""

from __future__ import annotations

import json

from detect_respond.domain.detections import Detection
from detect_respond.domain.events import AuditEvent


def render_alert(template: str, detection: Detection, event: AuditEvent) -> str:
    """Fill the template the way the rule's input transformer does: `{name}` fields from the detection when the rule is
    deployed, `<name>` fields from the event when it fires."""
    text = (
        template.replace("{id}", detection.detection_id)
        .replace("{title}", detection.title)
        .replace("{severity}", detection.severity)
        .replace("{first_step}", detection.first_step)
    )
    params = json.dumps(event.request, sort_keys=True, separators=(",", ":")) if event.request else "-"
    fields = {
        "time": str(event.raw["eventTime"]),
        "who": event.principal_arn or "-",
        "source": event.source,
        "name": event.name,
        "params": params,
        "ip": event.source_ip,
        "agent": event.user_agent,
        "region": event.region,
        "event_id": event.event_id,
    }
    for name, value in fields.items():
        text = text.replace(f"<{name}>", value)
    return text
