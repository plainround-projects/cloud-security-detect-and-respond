"""The lesson's drill and the offline pipeline, through `make`, as a reader runs them. Needs terraform and opa."""

import subprocess

import pytest

pytestmark = pytest.mark.e2e


def make(target: str) -> subprocess.CompletedProcess[str]:
    command = ["make", "--no-print-directory", target]
    return subprocess.run(command, capture_output=True, text=True, check=False, timeout=1200)


def test_both_environments_plan_validate_and_the_deployed_rules_equal_the_detection_files():
    result = make("validate")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "the plan deploys exactly the detections in detections/" in result.stdout
    assert "time to detect:  32 s" in result.stdout
    assert "time to contain: 6 min 52 s" in result.stdout
    assert "every logged file matches its digest" in result.stdout
    assert "is current" in result.stdout


def test_the_rehearsal_replay_on_its_own():
    result = make("demo-drill")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "6 alerts from detections: D1, D2, D4" in result.stdout
    assert "dry run, nothing changed" in result.stdout
