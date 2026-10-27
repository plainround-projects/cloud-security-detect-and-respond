"""IAM through boto3, with timeouts and retries."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import boto3
from botocore.config import Config


class BotoRevoker:
    """A `Revoker` over an IAM client."""

    def __init__(self, client: Any | None = None) -> None:
        self._iam = client or boto3.client(
            "iam", config=Config(retries={"max_attempts": 5, "mode": "standard"}, connect_timeout=3, read_timeout=10)
        )

    def list_access_keys(self, user_name: str) -> tuple[str, ...]:
        """The ids of the user's access keys, active or not."""
        response = self._iam.list_access_keys(UserName=user_name)
        return tuple(item["AccessKeyId"] for item in response["AccessKeyMetadata"])

    def put_role_policy(self, role_name: str, policy_name: str, policy: Mapping[str, Any]) -> None:
        """Attach (or replace) an inline policy; the call is idempotent."""
        self._iam.put_role_policy(RoleName=role_name, PolicyName=policy_name, PolicyDocument=json.dumps(policy))

    def deactivate_access_key(self, user_name: str, access_key_id: str) -> None:
        """Set the key inactive; the call is idempotent."""
        self._iam.update_access_key(UserName=user_name, AccessKeyId=access_key_id, Status="Inactive")
