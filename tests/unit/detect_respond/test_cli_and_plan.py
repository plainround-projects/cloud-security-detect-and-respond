import gzip
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

from detect_respond.domain.errors import PlanError
from detect_respond.infrastructure.files import DetectionDirectory
from detect_respond.infrastructure.plan_audit import ALL_EVENTS_STATE, audit_rules
from detect_respond.interfaces import cli
from detect_respond.interfaces.cli import main

DETECTIONS = DetectionDirectory(Path("detections")).detections()
ARCHIVE = "fixtures/drill"


def rule(module, detection_id, pattern, state="ENABLED"):
    name = f"{module.split('.')[1].replace('_', '-').replace('alerting-', 'detect-')}-{detection_id.lower()}"
    return {
        "type": "aws_cloudwatch_event_rule",
        "module_address": module,
        "change": {"after": {"name": name, "state": state, "event_pattern": json.dumps(pattern)}},
    }


def full_plan(honeytoken="AKIAPLANONLY00000000"):
    by_id = {d.detection_id: d for d in DETECTIONS}
    filled = by_id["D5"].with_parameters({"__HONEYTOKEN_ACCESS_KEY_ID__": honeytoken})
    changes = [
        rule("module.alerting_global", "D1", by_id["D1"].pattern),
        rule("module.alerting_global", "D3", by_id["D3"].pattern),
        rule("module.alerting_global", "D5", filled.pattern),
        rule("module.alerting_home", "D2", by_id["D2"].pattern),
        rule("module.alerting_watch_ap_southeast_2", "D4", by_id["D4"].pattern, ALL_EVENTS_STATE),
    ]
    return {"variables": {"honeytoken_access_key_id": {"value": honeytoken}}, "resource_changes": changes}


def write(tmp_path, plan):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    return path


def test_a_plan_that_deploys_exactly_the_detections_has_no_problems(tmp_path):
    assert audit_rules(write(tmp_path, full_plan()), DETECTIONS) == []


def test_a_detection_missing_from_where_it_belongs_is_a_problem(tmp_path):
    plan = full_plan()
    plan["resource_changes"] = [c for c in plan["resource_changes"] if not c["change"]["after"]["name"].endswith("-d2")]
    assert audit_rules(write(tmp_path, plan), DETECTIONS) == ["D2 is not deployed to home"]


def test_a_rule_whose_pattern_drifted_from_the_file_is_a_problem(tmp_path):
    plan = full_plan()
    plan["resource_changes"][0]["change"]["after"]["event_pattern"] = json.dumps(
        {"detail": {"eventName": ["CreateAccessKey"]}}
    )
    assert audit_rules(write(tmp_path, plan), DETECTIONS) == ["D1 in module.alerting_global differs from detections/"]


def test_d4_without_the_all_events_state_is_a_problem(tmp_path):
    plan = full_plan()
    plan["resource_changes"][-1]["change"]["after"]["state"] = "ENABLED"
    assert audit_rules(write(tmp_path, plan), DETECTIONS) == [
        "D4 must use the rule state that includes read-only management events"
    ]


def test_the_honeytoken_detection_is_skipped_when_its_variable_is_empty(tmp_path):
    plan = full_plan(honeytoken="")
    plan["resource_changes"] = [c for c in plan["resource_changes"] if not c["change"]["after"]["name"].endswith("-d5")]
    assert audit_rules(write(tmp_path, plan), DETECTIONS) == []


def test_a_plan_with_no_rules_is_an_error(tmp_path):
    with pytest.raises(PlanError, match="no event rules"):
        audit_rules(write(tmp_path, {"resource_changes": []}), DETECTIONS)


def test_scan_prints_alerts_and_checks_the_expected_detections(capsys):
    assert main(["scan", "--archive", ARCHIVE, "--expect", "D1,D2,D4"]) == 0
    output = capsys.readouterr().out
    assert "ALERT D1: new long-lived credential" in output
    assert "6 alerts from detections: D1, D2, D4" in output


def test_scan_fails_when_an_expected_detection_does_not_fire(capsys):
    assert main(["scan", "--archive", ARCHIVE, "--expect", "D3"]) == 1
    assert "expected but did not fire: D3" in capsys.readouterr().err


def test_scan_with_the_honeytoken_key_id_fires_d5(capsys):
    assert main(["scan", "--archive", ARCHIVE, "--honeytoken-key-id", "AKIADRILLEXAMPLE0001", "--expect", "D5"]) == 0
    assert "ALERT D5: honeytoken used" in capsys.readouterr().out


def test_drill_prints_the_timeline_and_the_two_times(capsys):
    assert main(["drill", "--archive", ARCHIVE, "--alerts", f"{ARCHIVE}/alerts.json"]) == 0
    output = capsys.readouterr().out
    assert "11:03:42  CreateAccessKey" in output
    assert "<- D1 fires" in output
    assert "time to detect:  32 s" in output
    assert "time to contain: 6 min 52 s" in output


def test_drill_without_an_attacker_session_exits_with_two(capsys):
    assert main(["drill", "--archive", ARCHIVE, "--session", "nobody"]) == 2
    assert "no call by the attacker" in capsys.readouterr().err


def test_review_is_written_then_verified_and_every_claim_cites_an_event(tmp_path, capsys):
    out = tmp_path / "review.md"
    common = ["review", "--archive", ARCHIVE, "--alerts", f"{ARCHIVE}/alerts.json"]
    assert main([*common, "--output", str(out)]) == 0
    assert main([*common, "--check", str(out)]) == 0
    text = out.read_text()
    assert "00000000-0000-4000-8000-000000000005" in text
    assert "no, recorded and alerted only" in text
    out.write_text("stale")
    assert main([*common, "--check", str(out)]) == 1
    assert "make review" in capsys.readouterr().err


def test_the_committed_review_is_current():
    assert (
        main(
            [
                "review",
                "--archive",
                ARCHIVE,
                "--alerts",
                f"{ARCHIVE}/alerts.json",
                "--check",
                "docs/REHEARSAL_REVIEW.md",
            ]
        )
        == 0
    )


def test_verify_archive_passes_on_the_fixture_and_fails_on_a_changed_file(tmp_path, capsys):
    assert main(["verify-archive", "--archive", ARCHIVE]) == 0
    shutil.copytree(ARCHIVE, tmp_path / "copy")
    log = next((tmp_path / "copy").rglob("*us-east-1*drill.json.gz"))
    log.write_bytes(log.read_bytes()[:-8] + b"tampered")
    assert main(["verify-archive", "--archive", str(tmp_path / "copy")]) in {1, 2}
    capsys.readouterr()


def test_verify_archive_without_digests_exits_with_one(tmp_path, capsys):
    assert main(["verify-archive", "--archive", str(tmp_path)]) == 1
    assert "no digest files" in capsys.readouterr().err


def test_posture_passes_on_the_fixture_and_fails_with_an_open_critical(tmp_path, capsys):
    assert main(["posture", "--findings", "fixtures/posture", "--accepted", "fixtures/posture/accepted.json"]) == 0
    assert "critical                    2               0                       0" in capsys.readouterr().out
    shutil.copytree("fixtures/posture", tmp_path / "p")
    (tmp_path / "p" / "after.json").write_text((tmp_path / "p" / "before.json").read_text())
    assert (
        main(["posture", "--findings", str(tmp_path / "p"), "--accepted", str(tmp_path / "p" / "accepted.json")]) == 1
    )
    assert "critical and neither fixed nor accepted" in capsys.readouterr().err


def test_contain_prints_a_dry_run_without_touching_the_account(capsys):
    assert main(["contain", "--access-key-id", "AKIADRILLEXAMPLE0001"]) == 0
    output = capsys.readouterr().out
    assert "dry run, nothing changed" in output
    assert "update-access-key --user-name drill-user --access-key-id AKIADRILLEXAMPLE0001 --status Inactive" in output


def test_contain_with_apply_calls_the_revoker(monkeypatch, capsys):
    calls: list[tuple[str, ...]] = []

    class Recorder:
        def list_access_keys(self, user_name):
            return ()

        def put_role_policy(self, role_name, policy_name, policy):
            calls.append(("put", role_name, policy_name))

        def deactivate_access_key(self, user_name, access_key_id):
            calls.append(("deactivate", access_key_id))

    monkeypatch.setattr(cli, "BotoRevoker", Recorder)
    assert main(["contain", "--access-key-id", "AKIADRILLEXAMPLE0001", "--apply"]) == 0
    assert calls == [("put", "drill-broad-role", "deny-all-before-now"), ("deactivate", "AKIADRILLEXAMPLE0001")]
    assert capsys.readouterr().out.startswith("applied")


def test_the_system_clock_is_timezone_aware():
    assert cli.SystemClock().now().tzinfo is not None


def test_audit_rules_command_reports_problems(tmp_path, capsys):
    plan = full_plan()
    plan["resource_changes"].pop(0)
    assert main(["audit-rules", "--plan", str(write(tmp_path, plan))]) == 1
    assert "problem: D1 is not deployed to global" in capsys.readouterr().out
    assert main(["audit-rules", "--plan", str(write(tmp_path, full_plan()))]) == 0


def test_a_missing_directory_exits_with_two(tmp_path, capsys):
    assert main(["scan", "--archive", str(tmp_path / "missing"), "--detections", str(tmp_path / "none")]) == 2
    capsys.readouterr()


def test_a_command_is_required():
    with pytest.raises(SystemExit):
        main([])


def test_the_committed_fixtures_are_what_the_generator_writes(tmp_path):
    spec = importlib.util.spec_from_file_location("make_drill_fixtures", "scripts/make_drill_fixtures.py")
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules["make_drill_fixtures"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    module.write(tmp_path / "drill")
    module.write_posture(tmp_path / "posture")
    for generated in sorted(tmp_path.rglob("*")):
        if generated.is_file():
            committed = Path("fixtures") / generated.relative_to(tmp_path)
            assert _content(committed) == _content(generated), committed


def _content(path):
    """The content; gzip files by their uncompressed bytes, because compressed bytes depend on the zlib build."""
    return gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
