import gzip
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import boto3
import pytest
from botocore.stub import Stubber

from detect_respond.application.use_cases import contain, posture_baseline, verify_archive
from detect_respond.domain.containment import POLICY_NAME, deny_sessions_before, plan_revocation
from detect_respond.domain.digest import verify_digest
from detect_respond.domain.errors import InvalidLogError
from detect_respond.domain.events import AuditEvent
from detect_respond.domain.posture import Acceptance, Finding, baseline
from detect_respond.infrastructure.boto_revoker import BotoRevoker
from detect_respond.infrastructure.files import PostureFiles
from detect_respond.infrastructure.log_archive import DirectoryArchive

NOW = datetime(2026, 10, 22, 11, 9, 48, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW


class FakeRevoker:
    def __init__(self, keys=("AKIADRILLEXAMPLE0001", "AKIATWO")):
        self.keys = keys
        self.calls = []

    def list_access_keys(self, user_name):
        self.calls.append(("list", user_name))
        return self.keys

    def put_role_policy(self, role_name, policy_name, policy):
        self.calls.append(("put", role_name, policy_name, policy["Statement"][0]["Condition"]))

    def deactivate_access_key(self, user_name, access_key_id):
        self.calls.append(("deactivate", user_name, access_key_id))


def test_the_revocation_denies_every_session_issued_before_the_moment_and_only_those():
    policy = deny_sessions_before(NOW)
    statement = policy["Statement"][0]
    assert statement["Effect"] == "Deny"
    assert statement["Action"] == "*"
    assert statement["Condition"] == {"DateLessThan": {"aws:TokenIssueTime": "2026-10-22T11:09:48Z"}}


def test_the_moment_is_written_in_utc_whatever_the_zone_of_the_clock():
    from datetime import timedelta, timezone

    local = datetime(2026, 10, 22, 13, 9, 48, tzinfo=timezone(timedelta(hours=2)))
    assert (
        deny_sessions_before(local)["Statement"][0]["Condition"]["DateLessThan"]["aws:TokenIssueTime"]
        == "2026-10-22T11:09:48Z"
    )


def test_a_dry_run_plans_and_changes_nothing():
    revoker = FakeRevoker()
    result = contain(revoker, FakeClock(), "drill-broad-role", "drill-user", (), apply=False)
    assert not result.applied
    assert result.plan.access_key_ids == ("AKIADRILLEXAMPLE0001", "AKIATWO")
    assert revoker.calls == [("list", "drill-user")]


def test_applying_revokes_the_sessions_first_and_then_every_key():
    revoker = FakeRevoker()
    contain(revoker, FakeClock(), "drill-broad-role", "drill-user", (), apply=True)
    assert [call[0] for call in revoker.calls] == ["list", "put", "deactivate", "deactivate"]
    assert revoker.calls[1][:3] == ("put", "drill-broad-role", POLICY_NAME)


def test_given_key_ids_are_used_without_listing():
    revoker = FakeRevoker()
    contain(revoker, FakeClock(), "r", "u", ("AKIAGIVEN",), apply=True)
    assert [call[0] for call in revoker.calls] == ["put", "deactivate"]


def test_the_plan_prints_the_same_actions_as_cli_commands():
    commands = plan_revocation("drill-broad-role", "drill-user", ("AKIADRILLEXAMPLE0001",), NOW).cli_commands()
    assert commands[0].startswith(
        "aws iam put-role-policy --role-name drill-broad-role --policy-name deny-all-before-now"
    )
    assert "aws:TokenIssueTime" in commands[0]
    assert (
        commands[1]
        == "aws iam update-access-key --user-name drill-user --access-key-id AKIADRILLEXAMPLE0001 --status Inactive"
    )


def test_the_boto_revoker_makes_the_three_iam_calls():
    iam = boto3.client("iam", region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="x")
    document = deny_sessions_before(NOW)
    with Stubber(iam) as stub:
        stub.add_response(
            "list_access_keys",
            {"AccessKeyMetadata": [{"AccessKeyId": "AKIADRILLEXAMPLE0001"}], "IsTruncated": False},
            {"UserName": "u"},
        )
        stub.add_response(
            "put_role_policy", {}, {"RoleName": "r", "PolicyName": "p", "PolicyDocument": json.dumps(document)}
        )
        stub.add_response(
            "update_access_key", {}, {"UserName": "u", "AccessKeyId": "AKIADRILLEXAMPLE0001", "Status": "Inactive"}
        )
        revoker = BotoRevoker(iam)
        assert revoker.list_access_keys("u") == ("AKIADRILLEXAMPLE0001",)
        revoker.put_role_policy("r", "p", document)
        revoker.deactivate_access_key("u", "AKIADRILLEXAMPLE0001")
        stub.assert_no_pending_responses()


def test_the_default_boto_revoker_builds_its_own_client(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    assert BotoRevoker() is not None


def test_an_untouched_archive_matches_its_digest():
    results = verify_archive(DirectoryArchive(Path("fixtures/drill")))
    assert [(r.checked, r.intact) for r in results] == [(3, True)]


def tampered_copy(tmp_path, change):
    shutil.copytree("fixtures/drill", tmp_path / "archive")
    log = next((tmp_path / "archive").rglob("*eu-west-1*drill.json.gz"))
    change(log)
    return DirectoryArchive(tmp_path / "archive")


def test_an_altered_log_file_no_longer_matches_its_digest(tmp_path):
    def alter(log):
        text = gzip.decompress(log.read_bytes()).decode().replace("public-read", "private")
        log.write_bytes(gzip.compress(text.encode(), mtime=0))

    result = verify_archive(tampered_copy(tmp_path, alter))[0]
    assert not result.intact
    assert len(result.mismatched) == 1
    assert "eu-west-1" in result.mismatched[0]


def test_a_deleted_log_file_is_reported_missing(tmp_path):
    result = verify_archive(tampered_copy(tmp_path, lambda log: log.unlink()))[0]
    assert len(result.missing) == 1
    assert not result.intact


def test_the_digest_compares_hashes_case_insensitively():
    import hashlib

    digest = {"logFiles": [{"s3Object": "a", "hashValue": hashlib.sha256(b"x").hexdigest().upper()}]}
    assert verify_digest(digest, lambda key: b"x").intact


def test_a_file_that_is_not_json_is_a_named_error(tmp_path):
    (tmp_path / "broken.json").write_text("{not json")
    with pytest.raises(InvalidLogError, match=r"broken\.json"):
        list(DirectoryArchive(tmp_path).events())


def test_a_record_without_an_event_id_is_a_named_error():
    with pytest.raises(InvalidLogError, match="eventID"):
        AuditEvent.from_record({"eventTime": "2026-10-22T11:03:42Z"})


def test_a_lookup_events_entry_wrapping_a_record_parses():
    wrapped = {
        "CloudTrailEvent": json.dumps(
            {"eventID": "x", "eventTime": "2026-10-22T11:03:42Z", "eventName": "N", "eventSource": "iam.amazonaws.com"}
        )
    }
    assert AuditEvent.from_record(wrapped).event_id == "x"


def test_a_bare_list_of_records_in_a_plain_file_is_read(tmp_path):
    record = {"eventID": "x", "eventTime": "2026-10-22T11:03:42Z", "eventName": "N", "eventSource": "iam.amazonaws.com"}
    (tmp_path / "events.json").write_text(json.dumps([record]))
    assert [e.event_id for e in DirectoryArchive(tmp_path).events()] == ["x"]
    assert DirectoryArchive(tmp_path).read_log("events.json") == json.dumps([record]).encode()


def asff(finding_id, severity, status="FAILED", workflow="NEW"):
    return {
        "Id": finding_id,
        "Title": finding_id,
        "Severity": {"Label": severity},
        "Compliance": {"Status": status},
        "Workflow": {"Status": workflow},
        "Resources": [{"Id": "r"}],
    }


def test_only_open_failures_are_findings():
    assert Finding.from_asff(asff("a", "HIGH")) is not None
    assert Finding.from_asff(asff("a", "HIGH", status="PASSED")) is None
    assert Finding.from_asff(asff("a", "HIGH", workflow="SUPPRESSED")) is None
    assert Finding.from_asff(asff("a", "HIGH", workflow="RESOLVED")) is None
    assert Finding.from_asff({**asff("a", "HIGH"), "Resources": []}).resource == ""  # type: ignore[union-attr]


def test_the_baseline_counts_open_accepted_and_fixed_findings():
    start = [Finding(f"c{i}", "t", "CRITICAL", "r") for i in range(2)] + [
        Finding(f"h{i}", "t", "HIGH", "r") for i in range(7)
    ]
    after = [Finding(f"h{i}", "t", "HIGH", "r") for i in range(7)]
    accepted = [Acceptance(f"h{i}", "sandbox only", "2026-10-22") for i in range(2, 7)]
    result = baseline(start, after, accepted)
    assert (result.start["CRITICAL"], result.after_fixing["CRITICAL"], result.accepted["CRITICAL"]) == (2, 0, 0)
    assert (result.start["HIGH"], result.after_fixing["HIGH"], result.accepted["HIGH"]) == (7, 2, 5)
    assert result.meets_done_when


def test_a_critical_finding_left_open_fails_the_done_when():
    result = baseline([Finding("c", "t", "CRITICAL", "r")], [Finding("c", "t", "CRITICAL", "r")], [])
    assert result.unaccepted_critical == ("c",)
    assert not result.meets_done_when


def test_an_acceptance_without_a_reason_does_not_count():
    result = baseline([], [Finding("c", "t", "CRITICAL", "r")], [Acceptance("c", "  ", "2026-10-22")])
    assert result.unaccepted_critical == ("c",)
    assert result.reasonless == ("c",)


def test_posture_files_read_the_fixture_baseline():
    source = PostureFiles(Path("fixtures/posture"), Path("fixtures/posture/accepted.json"))
    result = posture_baseline(source, "before.json", "after.json")
    assert result.meets_done_when
    assert (result.start["CRITICAL"], result.after_fixing["HIGH"], result.accepted["HIGH"]) == (2, 2, 5)
