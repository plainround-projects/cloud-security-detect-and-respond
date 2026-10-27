"""Write the synthetic audit archive of the rehearsal into fixtures/drill, byte for byte the same on every run.

The events follow the lesson's drill timeline (documentation addresses, a placeholder account, made-up key ids). The
archive has the layout of the real bucket: log files per Region and day, and a digest file listing each file's hash.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ACCOUNT = "000000000000"
SOURCE_IP = "203.0.113.25"
AGENT = "aws-cli/2.17.0 Python/3.12.4 command/iam.create-access-key"
USER = {
    "type": "IAMUser",
    "arn": f"arn:aws:iam::{ACCOUNT}:user/drill-user",
    "accessKeyId": "AKIADRILLEXAMPLE0001",
    "userName": "drill-user",
}
INTRUDER = {
    "type": "AssumedRole",
    "arn": f"arn:aws:sts::{ACCOUNT}:assumed-role/drill-broad-role/intruder",
    "accessKeyId": "ASIADRILLEXAMPLE0001",
}
RESPONDER = {
    "type": "AssumedRole",
    "arn": f"arn:aws:sts::{ACCOUNT}:assumed-role/security-admin/responder",
    "accessKeyId": "ASIARESPONDEREXAMPLE",
}
ADMIN = {
    "type": "AssumedRole",
    "arn": f"arn:aws:sts::{ACCOUNT}:assumed-role/sandbox-admin/setup",
    "accessKeyId": "ASIASETUPEXAMPLE0001",
}
ADMIN_POLICY = "arn:aws:iam::aws:policy/AdministratorAccess"
POWER_USER_POLICY = "arn:aws:iam::aws:policy/PowerUserAccess"


def record(
    number: int,
    time: str,
    name: str,
    source: str,
    region: str,
    who: dict[str, str],
    request: dict[str, Any] | None,
    error: str | None = None,
    ip: str = SOURCE_IP,
) -> dict[str, Any]:
    """One CloudTrail-shaped record with a stable event id."""
    body: dict[str, Any] = {
        "eventVersion": "1.10",
        "eventID": f"00000000-0000-4000-8000-{number:012d}",
        "eventTime": time,
        "eventName": name,
        "eventSource": source,
        "awsRegion": region,
        "sourceIPAddress": ip,
        "userAgent": AGENT,
        "userIdentity": who,
        "requestParameters": request,
        "recipientAccountId": ACCOUNT,
    }
    if error:
        body["errorCode"] = error
    return body


def events() -> dict[str, list[dict[str, Any]]]:
    """The drill's events, grouped by the log file they are delivered in."""
    iam, s3, ec2, sts = "iam.amazonaws.com", "s3.amazonaws.com", "ec2.amazonaws.com", "sts.amazonaws.com"
    broad_role = f"arn:aws:iam::{ACCOUNT}:role/drill-broad-role"
    return {
        "us-east-1": [
            record(
                1,
                "2026-10-22T10:50:11Z",
                "AttachRolePolicy",
                iam,
                "us-east-1",
                ADMIN,
                {"roleName": "drill-broad-role", "policyArn": POWER_USER_POLICY},
                ip="198.51.100.7",
            ),
            record(
                2,
                "2026-10-22T10:52:30Z",
                "CreateAccessKey",
                iam,
                "us-east-1",
                ADMIN,
                {"userName": "drill-user"},
                ip="198.51.100.7",
            ),
            record(
                3,
                "2026-10-22T11:03:10Z",
                "AssumeRole",
                sts,
                "us-east-1",
                USER,
                {"roleArn": broad_role, "roleSessionName": "intruder"},
            ),
            record(
                5, "2026-10-22T11:03:42Z", "CreateAccessKey", iam, "us-east-1", INTRUDER, {"userName": "drill-user"}
            ),
            record(
                8,
                "2026-10-22T11:09:48Z",
                "PutRolePolicy",
                iam,
                "us-east-1",
                RESPONDER,
                {"roleName": "drill-broad-role", "policyName": "deny-all-before-now"},
                ip="198.51.100.7",
            ),
            record(
                9,
                "2026-10-22T11:09:57Z",
                "UpdateAccessKey",
                iam,
                "us-east-1",
                RESPONDER,
                {"userName": "drill-user", "accessKeyId": "AKIADRILLEXAMPLE0001", "status": "Inactive"},
                ip="198.51.100.7",
            ),
            record(
                10,
                "2026-10-22T11:10:02Z",
                "CreateAccessKey",
                iam,
                "us-east-1",
                INTRUDER,
                {"userName": "drill-user"},
                error="AccessDenied",
            ),
        ],
        "eu-west-1": [
            record(4, "2026-10-22T11:03:21Z", "ListBuckets", s3, "eu-west-1", INTRUDER, None),
            record(
                6,
                "2026-10-22T11:04:05Z",
                "PutBucketAcl",
                s3,
                "eu-west-1",
                INTRUDER,
                {"bucketName": f"drill-data-{ACCOUNT}", "x-amz-acl": ["public-read"]},
            ),
            record(
                11,
                "2026-10-22T11:20:00Z",
                "PutBucketAcl",
                s3,
                "eu-west-1",
                RESPONDER,
                {"bucketName": f"drill-data-{ACCOUNT}", "x-amz-acl": ["private"]},
                ip="198.51.100.7",
            ),
        ],
        "ap-southeast-2": [
            record(
                7,
                "2026-10-22T11:04:31Z",
                "DescribeInstances",
                ec2,
                "ap-southeast-2",
                INTRUDER,
                {"instancesSet": {}, "filterSet": {}},
            ),
        ],
    }


def write(target: Path) -> list[Path]:
    """Write the log files and the digest under `target` and return the paths."""
    written, listed = [], []
    for region, records in events().items():
        folder = f"AWSLogs/{ACCOUNT}/CloudTrail/{region}/2026/10/22"
        key = f"{folder}/{ACCOUNT}_CloudTrail_{region}_20261022T1130Z_drill.json.gz"
        content = json.dumps({"Records": records}, sort_keys=True, indent=2).encode()
        path = target / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(content, compresslevel=6, mtime=0))
        written.append(path)
        times = sorted(r["eventTime"] for r in records)
        listed.append(
            {
                "s3Object": key,
                "hashValue": hashlib.sha256(content).hexdigest(),
                "hashAlgorithm": "SHA-256",
                "newestEventTime": times[-1],
                "oldestEventTime": times[0],
            }
        )
    digest_folder = f"AWSLogs/{ACCOUNT}/CloudTrail-Digest/eu-west-1/2026/10/22"
    digest_key = f"{digest_folder}/{ACCOUNT}_CloudTrail-Digest_eu-west-1_drill_20261022T1140Z.json.gz"
    digest = {
        "awsAccountId": ACCOUNT,
        "digestStartTime": "2026-10-22T10:40:00Z",
        "digestEndTime": "2026-10-22T11:40:00Z",
        "digestPublicKeyFingerprint": "0000000000000000000000000000000000000000",
        "digestSignatureAlgorithm": "SHA256withRSA",
        "previousDigestHashValue": None,
        "logFiles": listed,
    }
    path = target / digest_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(digest, sort_keys=True, indent=2).encode(), compresslevel=6, mtime=0))
    written.append(path)
    alerts = {
        "alerts": [
            {"eventId": e["eventID"], "receivedAt": e["eventTime"]}
            for rs in events().values()
            for e in rs
            if e["eventID"][-2:] in {"05", "06", "07"}
        ]
    }
    (target / "alerts.json").write_text(json.dumps(alerts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return written


STANDARD = f"arn:aws:securityhub:eu-west-1:{ACCOUNT}:subscription/aws-foundational-security-best-practices/v/1.0.0"
CRITICAL = [
    ("S3.2", "S3 buckets should prohibit public read access"),
    ("EC2.13", "Security groups should not allow ingress from 0.0.0.0/0 to port 22"),
]
HIGH = [
    ("IAM.1", "IAM policies should not allow full administrative privileges"),
    ("IAM.6", "Hardware MFA should be enabled for the root user"),
    ("S3.5", "S3 buckets should require requests to use TLS"),
    ("S3.1", "S3 general purpose buckets should have block public access settings enabled"),
    ("EC2.2", "The VPC default security group should not allow inbound and outbound traffic"),
    ("CloudTrail.1", "CloudTrail should be enabled and configured with at least one multi-Region trail"),
    ("KMS.4", "KMS key rotation should be enabled"),
]


def finding(number: int, control: str, title: str, severity: str) -> dict[str, Any]:
    """One finding in the posture service's format, reduced to the fields the baseline reads."""
    return {
        "Id": f"{STANDARD}/{control}/finding/00000000-0000-4000-8000-{number:012d}",
        "Title": f"{control} {title}",
        "Severity": {"Label": severity},
        "Compliance": {"Status": "FAILED"},
        "Workflow": {"Status": "NEW"},
        "Resources": [{"Id": f"arn:aws:s3:::example-resource-{number}"}],
    }


def write_posture(target: Path) -> list[Path]:
    """The lesson's example baseline: 2 critical and 7 high at the start; after fixing, 7 high, 5 of them accepted."""
    target.mkdir(parents=True, exist_ok=True)
    critical = [finding(i, c, t, "CRITICAL") for i, (c, t) in enumerate(CRITICAL, start=1)]
    high = [finding(i, c, t, "HIGH") for i, (c, t) in enumerate(HIGH, start=10)]
    files = {
        "before.json": {"Findings": critical + high},
        "after.json": {"Findings": high},
        "accepted.json": {
            "accepted": [
                {"findingId": f["Id"], "reason": reason, "acceptedOn": "2026-10-22"}
                for f, reason in zip(
                    high[2:],
                    [
                        "Sandbox bucket holds no data and is deleted the same day.",
                        "No workload serves traffic from this account.",
                        "The drill bucket is public on purpose; see the exception in the review.",
                        "A sandbox account has no multi-Region workload.",
                        "Key is deleted with the sandbox.",
                    ],
                    strict=True,
                )
            ]
        },
    }
    paths = []
    for name, body in files.items():
        path = target / name
        path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def main() -> int:
    """Command line: make_drill_fixtures.py [fixtures_dir]; writes drill/ and posture/ under it."""
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures")
    archive = write(target / "drill")
    posture = write_posture(target / "posture")
    print(f"wrote {len(archive)} archive files, alerts.json and {len(posture)} posture files under {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
