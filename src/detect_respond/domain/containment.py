"""Containment: stop a role's sessions, not only the key. Revoking the key leaves sessions already issued alive."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

POLICY_NAME = "deny-all-before-now"


def deny_sessions_before(moment: datetime) -> dict[str, Any]:
    """An inline policy that denies every call made with credentials issued before `moment`. New sessions, issued after
    the moment, are unaffected, so the role can be used again once the cause is fixed."""
    stamp = moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DenySessionsIssuedBeforeContainment",
                "Effect": "Deny",
                "Action": "*",
                "Resource": "*",
                "Condition": {"DateLessThan": {"aws:TokenIssueTime": stamp}},
            }
        ],
    }


@dataclass(frozen=True)
class RevocationPlan:
    """What containment will do, so it can be shown before it is done."""

    role_name: str
    user_name: str
    policy_name: str
    policy: dict[str, Any]
    access_key_ids: tuple[str, ...]

    def cli_commands(self) -> list[str]:
        """The same actions as AWS CLI commands, for a responder who prefers to run them by hand."""
        commands = [
            f"aws iam put-role-policy --role-name {self.role_name} --policy-name {self.policy_name} "
            f"--policy-document '{json.dumps(self.policy, separators=(',', ':'))}'"
        ]
        commands += [
            f"aws iam update-access-key --user-name {self.user_name} --access-key-id {key} --status Inactive"
            for key in self.access_key_ids
        ]
        return commands


def plan_revocation(role_name: str, user_name: str, access_key_ids: tuple[str, ...], now: datetime) -> RevocationPlan:
    """Plan the revocation of one role's sessions and one user's keys as of `now`."""
    return RevocationPlan(role_name, user_name, POLICY_NAME, deny_sessions_before(now), access_key_ids)
