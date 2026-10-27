"""What the use cases need from the outside."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any, Protocol

from detect_respond.domain.detections import Detection
from detect_respond.domain.events import AuditEvent
from detect_respond.domain.posture import Acceptance, Finding


class LogArchive(Protocol):
    """The central log store, read back from files synced out of the archive bucket."""

    def events(self) -> Iterable[AuditEvent]:
        """Every event in the archive."""
        ...

    def digests(self) -> Iterable[Mapping[str, Any]]:
        """Every digest file in the archive."""
        ...

    def read_log(self, s3_object: str) -> bytes | None:
        """The uncompressed content of a log file, or None when the archive does not have it."""
        ...


class DetectionCatalog(Protocol):
    """The detections and the alert template, kept as files."""

    def detections(self) -> tuple[Detection, ...]:
        """All detections."""
        ...

    def template(self) -> str:
        """The alert text template."""
        ...


class Revoker(Protocol):
    """Changes access in the account. The only port that writes."""

    def list_access_keys(self, user_name: str) -> tuple[str, ...]:
        """The ids of the user's access keys."""
        ...

    def put_role_policy(self, role_name: str, policy_name: str, policy: Mapping[str, Any]) -> None:
        """Attach an inline policy to the role."""
        ...

    def deactivate_access_key(self, user_name: str, access_key_id: str) -> None:
        """Make the key unusable without deleting it."""
        ...


class Clock(Protocol):
    """The current time, injected so containment is testable."""

    def now(self) -> datetime:
        """An aware datetime."""
        ...


class PostureSource(Protocol):
    """Findings and accepted risks from files."""

    def findings(self, name: str) -> tuple[Finding, ...]:
        """Open findings from the named file."""
        ...

    def acceptances(self) -> tuple[Acceptance, ...]:
        """The accepted risks."""
        ...
