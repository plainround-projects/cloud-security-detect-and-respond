"""Builders for audit events and plans."""

from __future__ import annotations

from typing import Any

from detect_respond.domain.events import AuditEvent

ACCOUNT = "000000000000"
INTRUDER_ARN = f"arn:aws:sts::{ACCOUNT}:assumed-role/drill-broad-role/intruder"


def event(
    name: str,
    *,
    source: str = "iam.amazonaws.com",
    region: str = "us-east-1",
    request: dict[str, Any] | None = None,
    arn: str = INTRUDER_ARN,
    access_key_id: str = "ASIAEXAMPLE000000001",
    error: str | None = None,
    time: str = "2026-10-22T11:03:42Z",
    event_id: str = "e-1",
) -> AuditEvent:
    """One audit event with sensible defaults."""
    record: dict[str, Any] = {
        "eventID": event_id,
        "eventTime": time,
        "eventName": name,
        "eventSource": source,
        "awsRegion": region,
        "sourceIPAddress": "203.0.113.25",
        "userAgent": "aws-cli/2.17.0",
        "userIdentity": {"arn": arn, "accessKeyId": access_key_id},
        "requestParameters": request,
    }
    if error:
        record["errorCode"] = error
    return AuditEvent.from_record(record)
