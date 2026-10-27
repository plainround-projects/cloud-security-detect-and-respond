"""Text and Markdown output: alerts, the timeline, measured times, archive check, posture table and review."""

from __future__ import annotations

from detect_respond.application.use_cases import Alert, Drill
from detect_respond.domain.digest import DigestResult
from detect_respond.domain.drill import DrillMeasure, format_duration
from detect_respond.domain.events import AuditEvent
from detect_respond.domain.posture import SEVERITIES, Baseline
from detect_respond.domain.timeline import TimelineEntry


def _target(event: AuditEvent) -> str:
    request = event.request
    if event.name == "AssumeRole":
        return f'{str(request.get("roleArn", "")).rsplit("/", 1)[-1]} session "{request.get("roleSessionName", "")}"'
    for field in ("userName", "bucketName", "roleName"):
        if field in request:
            acl = request.get("x-amz-acl")
            return f"{request[field]} ({acl[0]})" if field == "bucketName" and acl else str(request[field])
    if event.name.startswith("Describe"):
        return event.region
    return "-"


def _clock(event: AuditEvent) -> str:
    return event.time.strftime("%H:%M:%S")


def timeline_line(entry: TimelineEntry) -> str:
    """One line per call: time, name, target, result, and which detection it raises."""
    event = entry.event
    who = "(responder) " if entry.actor == "responder" else ""
    result = "DENIED" if event.denied else "OK"
    marks = f"  <- {', '.join(entry.detections)} fires" if entry.detections else ""
    return f"{_clock(event)}  {who}{event.name:<18} {_target(event):<40} {result:<7}{marks}".rstrip()


def measure_lines(measured: DrillMeasure) -> list[str]:
    """The two numbers, in the lesson's wording."""
    alert = f"first alert {_at(measured.first_alert)}" if measured.first_alert else "no alert"
    refused = (
        f"next call refused {_at(measured.contained_at)}"
        if measured.contained_at
        else "the attacker made no call after the revocation"
    )
    first = _at(measured.first_action)
    return [
        f"time to detect:  {format_duration(measured.time_to_detect)}  (first action {first}, {alert})",
        f"time to contain: {format_duration(measured.time_to_contain)}  (first action {first}, {refused})",
    ]


def _at(moment: object) -> str:
    return moment.strftime("%H:%M:%S") if hasattr(moment, "strftime") else str(moment)


def alert_blocks(alerts: tuple[Alert, ...]) -> str:
    """The alerts as the responder would receive them."""
    return "\n\n".join(alert.text.rstrip() for alert in alerts)


def archive_lines(results: tuple[DigestResult, ...]) -> list[str]:
    """One line per digest, then a verdict."""
    lines = [
        f"digest {index}: {result.checked} files checked, {len(result.mismatched)} changed, "
        f"{len(result.missing)} missing"
        for index, result in enumerate(results, start=1)
    ]
    for result in results:
        lines += [f"  CHANGED {name}" for name in result.mismatched] + [f"  MISSING {name}" for name in result.missing]
    return lines


def posture_lines(result: Baseline) -> list[str]:
    """The baseline table of the lesson."""
    lines = ["severity    findings at start    after fixing    accepted with reason"]
    for severity in SEVERITIES:
        start, after, accepted = (
            counts.get(severity, 0) for counts in (result.start, result.after_fixing, result.accepted)
        )
        lines.append(f"{severity.lower():<11} {start:>17} {after:>15} {accepted:>23}")
    return lines


def review_markdown(drill: Drill, detections: dict[str, tuple[str, str]]) -> str:
    """A blameless review of the drill, built from the logs alone. `detections` maps an id to (title, prevention)."""
    lines = [
        "# Incident review: drill",
        "",
        "Blameless wording: the role allowed the calls below. Every claim cites an event id from the central archive.",
        "",
        "## Timeline, from the logs only",
        "",
        "| Time (UTC) | Actor | Call | Target | Result | Event id | Detection |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in drill.timeline:
        event = entry.event
        lines.append(
            f"| {_clock(event)} | {entry.actor} | {event.name} | {_target(event)} "
            f"| {'denied' if event.denied else 'ok'} | {event.event_id} | {', '.join(entry.detections) or '-'} |"
        )
    lines += [
        "",
        "## Times",
        "",
        *[f"- {line}" for line in measure_lines(drill.measured)],
        "",
        "## Prevented and only recorded",
        "",
    ]
    lines += [
        "| Detection | Raised by (event id) | Prevented? | What prevention would look like |",
        "| --- | --- | --- | --- |",
    ]
    for detection_id in drill.measured.detections:
        title, prevention = detections[detection_id]
        raised = [e for e in drill.timeline if detection_id in e.detections]
        prevented = all(entry.event.denied for entry in raised)
        cited = ", ".join(entry.event.event_id for entry in raised)
        outcome = "yes" if prevented else "no, recorded and alerted only"
        lines.append(f"| {detection_id} {title} | {cited} | {outcome} | {prevention} |")
    lines += [
        "",
        "## Changes that would stop the weakness recurring",
        "",
        *[f"- {detections[d][1]}" for d in drill.measured.detections if detections[d][1]],
        "- Remove the temporary exception (the drill user, the broad role and the drill bucket) and write down the "
        "time: `make down`.",
        "",
    ]
    return "\n".join(lines)
