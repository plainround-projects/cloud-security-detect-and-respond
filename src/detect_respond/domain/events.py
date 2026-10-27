"""An audit-log event, parsed once from a CloudTrail record."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from detect_respond.domain.errors import InvalidLogError

DENIAL_CODES = ("AccessDenied", "AccessDeniedException", "Client.UnauthorizedOperation", "UnauthorizedOperation")


def parse_time(text: str) -> datetime:
    """Parse the `2026-10-22T11:03:42Z` timestamps of the audit log into aware datetimes."""
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


@dataclass(frozen=True)
class AuditEvent:
    """The fields of one record that detections, timelines and drills use. `raw` keeps the whole record."""

    event_id: str
    time: datetime
    name: str
    source: str
    region: str
    principal_arn: str
    access_key_id: str
    source_ip: str
    user_agent: str
    error_code: str | None
    request: Mapping[str, Any]
    raw: Mapping[str, Any] = field(repr=False, compare=False)

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> AuditEvent:
        """Build an event from a CloudTrail record, or from a `lookup-events` entry that wraps one."""
        if "CloudTrailEvent" in record:
            record = json.loads(record["CloudTrailEvent"])
        try:
            identity = record.get("userIdentity") or {}
            return cls(
                event_id=record["eventID"],
                time=parse_time(record["eventTime"]),
                name=record["eventName"],
                source=record["eventSource"],
                region=record.get("awsRegion", ""),
                principal_arn=identity.get("arn", ""),
                access_key_id=identity.get("accessKeyId", ""),
                source_ip=record.get("sourceIPAddress", ""),
                user_agent=record.get("userAgent", ""),
                error_code=record.get("errorCode"),
                request=record.get("requestParameters") or {},
                raw=record,
            )
        except KeyError as error:
            raise InvalidLogError(f"a record lacks the field {error}") from error

    @property
    def denied(self) -> bool:
        """True when the call failed because the caller was not allowed."""
        return self.error_code in DENIAL_CODES

    @property
    def service(self) -> str:
        """The service prefix, for example `iam` for `iam.amazonaws.com`."""
        return self.source.split(".")[0]

    def envelope(self) -> dict[str, Any]:
        """The event as EventBridge delivers it to a rule, which is what detection patterns match against."""
        return {
            "source": f"aws.{self.service}",
            "detail-type": "AWS API Call via CloudTrail",
            "region": self.region,
            "time": self.raw["eventTime"],
            "detail": dict(self.raw),
        }

    def session_of(self, role_name: str) -> str | None:
        """The session name when this event was made by a session of the role, otherwise None."""
        marker = f":assumed-role/{role_name}/"
        if marker in self.principal_arn:
            return self.principal_arn.split(marker, 1)[1]
        return None
