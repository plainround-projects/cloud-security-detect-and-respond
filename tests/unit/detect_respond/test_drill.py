from datetime import timedelta
from pathlib import Path

import pytest

from detect_respond.application.use_cases import run_drill, scan_logs
from detect_respond.domain.alerts import render_alert
from detect_respond.domain.drill import format_duration, measure
from detect_respond.domain.errors import DrillError
from detect_respond.domain.events import parse_time
from detect_respond.domain.timeline import build_timeline
from detect_respond.infrastructure.files import DetectionDirectory
from detect_respond.infrastructure.log_archive import DirectoryArchive
from tests.builders import event

ARCHIVE = DirectoryArchive(Path("fixtures/drill"))
CATALOG = DetectionDirectory(Path("detections"))
RULES = CATALOG.detections()


def drill(alert_times=None):
    return run_drill(ARCHIVE, CATALOG, "drill-broad-role", "intruder", "drill-user", alert_times or {})


def test_the_timeline_is_rebuilt_from_the_archive_alone_denied_calls_included():
    entries = drill().timeline
    assert [(e.event.name, e.actor, e.event.denied) for e in entries] == [
        ("AssumeRole", "attacker", False),
        ("ListBuckets", "attacker", False),
        ("CreateAccessKey", "attacker", False),
        ("PutBucketAcl", "attacker", False),
        ("DescribeInstances", "attacker", False),
        ("PutRolePolicy", "responder", False),
        ("UpdateAccessKey", "responder", False),
        ("CreateAccessKey", "attacker", True),
    ]


def test_setup_calls_and_other_principals_are_not_in_the_timeline():
    ids = {e.event.event_id[-2:] for e in drill().timeline}
    assert "01" not in ids
    assert "02" not in ids
    assert "11" not in ids


def test_the_detections_that_fire_are_the_lessons_d1_d2_d4():
    assert drill().measured.detections == ("D1", "D2", "D4")


def test_time_to_detect_and_time_to_contain_match_the_lessons_example():
    measured = drill().measured
    assert measured.first_action == parse_time("2026-10-22T11:03:10Z")
    assert format_duration(measured.time_to_detect) == "32 s"
    assert format_duration(measured.time_to_contain) == "6 min 52 s"


def test_a_late_first_alert_hands_the_clock_to_the_next_detection_but_does_not_change_time_to_contain():
    delivered = {"00000000-0000-4000-8000-000000000005": parse_time("2026-10-22T11:05:10Z")}
    measured = drill(delivered).measured
    assert format_duration(measured.time_to_detect) == "55 s"  # the public-bucket alert (11:04:05) is now the first
    assert format_duration(measured.time_to_contain) == "6 min 52 s"


def test_without_a_revocation_there_is_no_time_to_contain():
    events = [e for e in ARCHIVE.events() if e.name != "PutRolePolicy"]
    entries = build_timeline(events, RULES, "drill-broad-role", "intruder", "drill-user")
    measured = measure(entries, {})
    assert measured.revoked_at is None
    assert measured.contained_at is None
    assert format_duration(measured.time_to_contain) == "not measured"


def test_a_revocation_the_attacker_never_tests_leaves_containment_unconfirmed():
    events = [e for e in ARCHIVE.events() if e.event_id[-2:] != "10"]
    entries = build_timeline(events, RULES, "drill-broad-role", "intruder", "drill-user")
    measured = measure(entries, {})
    assert measured.revoked_at is not None
    assert measured.contained_at is None


def test_no_attacker_calls_is_an_error():
    with pytest.raises(DrillError, match="no call"):
        measure(
            build_timeline(
                [event("ListBuckets", arn="arn:aws:iam::0:user/x")], RULES, "drill-broad-role", "intruder", "drill-user"
            ),
            {},
        )


def test_a_session_with_no_detection_has_no_alert_time():
    entries = build_timeline(
        [event("ListBuckets", source="s3.amazonaws.com", region="eu-west-1")],
        RULES,
        "drill-broad-role",
        "intruder",
        "drill-user",
    )
    measured = measure(entries, {})
    assert measured.first_alert is None
    assert measured.time_to_detect is None


@pytest.mark.parametrize(("seconds", "text"), [(0, "0 s"), (59, "59 s"), (60, "1 min 0 s"), (412, "6 min 52 s")])
def test_durations_read_as_seconds_or_minutes_and_seconds(seconds, text):
    assert format_duration(timedelta(seconds=seconds)) == text


def test_scanning_the_archive_finds_every_firing_including_the_setup_key_and_the_retry():
    alerts = scan_logs(ARCHIVE, CATALOG, {})
    assert [(a.detection.detection_id, a.event.event_id[-2:]) for a in alerts] == [
        ("D1", "02"),
        ("D1", "05"),
        ("D2", "06"),
        ("D4", "07"),
        ("D1", "10"),
        ("D2", "11"),
    ]


def test_scanning_with_the_honeytoken_key_adds_d5():
    alerts = scan_logs(ARCHIVE, CATALOG, {"__HONEYTOKEN_ACCESS_KEY_ID__": "AKIADRILLEXAMPLE0001"})
    assert {a.detection.detection_id for a in alerts if a.event.access_key_id == "AKIADRILLEXAMPLE0001"} == {"D5"}


def test_an_alert_carries_who_what_from_where_and_the_first_step():
    first = scan_logs(ARCHIVE, CATALOG, {})[1]
    text = first.text
    assert text.startswith("ALERT D1: new long-lived credential")
    assert "who:      arn:aws:sts::000000000000:assumed-role/drill-broad-role/intruder" in text
    assert 'what:     iam.amazonaws.com CreateAccessKey {"userName":"drill-user"}' in text
    assert "from:     203.0.113.25" in text
    assert "first step: Ask who made it; disable it" in text
    assert "<" not in text
    assert "{" not in text.replace('{"userName":"drill-user"}', "")


def test_an_event_with_no_request_renders_a_dash():
    quiet = event("ListBuckets", source="s3.amazonaws.com")
    assert "ListBuckets -" in render_alert(CATALOG.template(), RULES[0], quiet)
