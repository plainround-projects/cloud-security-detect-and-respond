import json
from pathlib import Path

import pytest

from detect_respond.domain.detections import Detection
from detect_respond.domain.errors import InvalidDetectionError, UnsupportedPatternError
from detect_respond.domain.pattern import matches
from detect_respond.infrastructure.files import DetectionDirectory
from tests.builders import event

DETECTIONS = {d.detection_id: d for d in DetectionDirectory(Path("detections")).detections()}


@pytest.mark.parametrize(
    ("pattern", "target", "expected"),
    [
        ({"a": ["x"]}, {"a": "x"}, True),
        ({"a": ["x", "y"]}, {"a": "y"}, True),
        ({"a": ["x"]}, {"a": "z"}, False),
        ({"a": ["x"]}, {}, False),
        ({"a": [False]}, {"a": False}, True),
        ({"a": [False]}, {"a": True}, False),
        ({"a": ["x"]}, {"a": ["w", "x"]}, True),
        ({"a": {"b": ["x"]}}, {"a": {"b": "x"}}, True),
        ({"a": {"b": ["x"]}}, {"a": "x"}, False),
        ({"a": {"b": ["x"]}}, {}, False),
        ({"a": [{"anything-but": ["x"]}]}, {"a": "y"}, True),
        ({"a": [{"anything-but": ["x"]}]}, {"a": "x"}, False),
        ({"a": [{"anything-but": "x"}]}, {"a": "y"}, True),
        ({"a": [{"anything-but": ["x"]}]}, {}, False),
        ({"a": [{"prefix": "ab"}]}, {"a": "abc"}, True),
        ({"a": [{"prefix": "ab"}]}, {"a": "xab"}, False),
        ({"a": [{"suffix": "bc"}]}, {"a": "abc"}, True),
        ({"a": [{"suffix": "bc"}]}, {"a": 5}, False),
        ({"a": [{"exists": True}]}, {"a": None}, True),
        ({"a": [{"exists": False}]}, {}, True),
        ({"a": [{"exists": False}]}, {"a": 1}, False),
        ({"$or": [{"a": ["x"]}, {"b": ["y"]}]}, {"b": "y"}, True),
        ({"$or": [{"a": ["x"]}, {"b": ["y"]}]}, {"b": "z"}, False),
        ({"c": ["k"], "$or": [{"a": ["x"]}, {"b": ["y"]}]}, {"a": "x"}, False),
    ],
)
def test_the_matcher_follows_the_event_pattern_language(pattern, target, expected):
    assert matches(pattern, target) is expected


@pytest.mark.parametrize("operator", [{"numeric": [">", 1]}, {"anything-but": "x", "prefix": "y"}])
def test_an_operator_the_matcher_does_not_implement_raises_instead_of_never_matching(operator):
    with pytest.raises(UnsupportedPatternError):
        matches({"a": [operator]}, {"a": 1})


def test_d1_fires_on_a_new_access_key_or_console_password_even_when_denied():
    assert DETECTIONS["D1"].fires(event("CreateAccessKey", request={"userName": "drill-user"}))
    assert DETECTIONS["D1"].fires(event("CreateLoginProfile", request={"userName": "drill-user"}))
    assert DETECTIONS["D1"].fires(event("CreateAccessKey", error="AccessDenied"))


@pytest.mark.parametrize(
    "near_miss",
    [
        event("DeleteAccessKey"),
        event("ListAccessKeys"),
        event("CreateAccessKey", source="sts.amazonaws.com"),
    ],
)
def test_d1_ignores_near_misses(near_miss):
    assert not DETECTIONS["D1"].fires(near_miss)


@pytest.mark.parametrize("name", ["PutBucketPolicy", "PutBucketAcl", "DeletePublicAccessBlock"])
def test_d2_fires_on_a_change_that_can_make_storage_public(name):
    assert DETECTIONS["D2"].fires(event(name, source="s3.amazonaws.com", region="eu-west-1"))


def test_d2_fires_on_a_public_access_block_that_switches_a_setting_off_only():
    off = {
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": True,
        }
    }
    on = {
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        }
    }
    assert DETECTIONS["D2"].fires(event("PutPublicAccessBlock", source="s3.amazonaws.com", request=off))
    assert not DETECTIONS["D2"].fires(event("PutPublicAccessBlock", source="s3.amazonaws.com", request=on))
    assert not DETECTIONS["D2"].fires(event("PutBucketVersioning", source="s3.amazonaws.com"))


@pytest.mark.parametrize("name", ["AttachUserPolicy", "AttachRolePolicy", "AttachGroupPolicy"])
def test_d3_fires_only_when_the_administrator_policy_is_attached(name):
    admin = {"policyArn": "arn:aws:iam::aws:policy/AdministratorAccess"}
    power = {"policyArn": "arn:aws:iam::aws:policy/PowerUserAccess"}
    assert DETECTIONS["D3"].fires(event(name, request=admin))
    assert not DETECTIONS["D3"].fires(event(name, request=power))


def test_d4_fires_in_a_region_outside_the_list_and_for_read_only_calls():
    describe = event("DescribeInstances", source="ec2.amazonaws.com", region="ap-southeast-2")
    assert DETECTIONS["D4"].fires(describe)
    assert not DETECTIONS["D4"].fires(event("DescribeInstances", source="ec2.amazonaws.com", region="eu-west-1"))
    assert not DETECTIONS["D4"].fires(event("ListBuckets", source="s3.amazonaws.com", region="us-east-1"))


def test_d5_never_fires_until_its_placeholder_is_filled_then_fires_on_that_key_only():
    honeytoken = DETECTIONS["D5"]
    used = event("GetCallerIdentity", source="sts.amazonaws.com", access_key_id="AKIAHONEYTOKEN00001")
    assert not honeytoken.complete
    assert not honeytoken.fires(used)
    filled = honeytoken.with_parameters({"__HONEYTOKEN_ACCESS_KEY_ID__": "AKIAHONEYTOKEN00001"})
    assert filled.complete
    assert filled.fires(used)
    assert not filled.fires(
        event("GetCallerIdentity", source="sts.amazonaws.com", access_key_id="ASIAEXAMPLE000000001")
    )


def test_every_detection_has_a_severity_a_first_step_a_prevention_and_a_place_to_run():
    assert sorted(DETECTIONS) == ["D1", "D2", "D3", "D4", "D5"]
    for detection in DETECTIONS.values():
        assert detection.first_step
        assert detection.prevention
        assert detection.deploy_to


def raw_detection(**changes):
    base = json.loads(Path("detections/d1-new-long-lived-credential.json").read_text())
    return {**base, **changes}


def test_a_detection_with_a_bad_severity_is_rejected():
    with pytest.raises(InvalidDetectionError, match="severity"):
        Detection.from_mapping(raw_detection(severity="urgent"))


def test_a_detection_with_an_unknown_target_is_rejected():
    with pytest.raises(InvalidDetectionError, match="deployTo"):
        Detection.from_mapping(raw_detection(deployTo=["moon"]))


def test_a_detection_missing_a_field_is_rejected():
    raw = raw_detection()
    del raw["pattern"]
    with pytest.raises(InvalidDetectionError, match="pattern"):
        Detection.from_mapping(raw)


def test_a_folder_with_duplicate_ids_is_rejected(tmp_path):
    for name in ("d1-a.json", "d1-b.json"):
        (tmp_path / name).write_text(json.dumps(raw_detection()))
    with pytest.raises(InvalidDetectionError, match="unique"):
        DetectionDirectory(tmp_path).detections()
