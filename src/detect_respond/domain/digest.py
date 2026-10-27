"""Tamper evidence for the archive: the digest files list a SHA-256 hash for every log file."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DigestResult:
    """How many logged files matched their digest, and which did not."""

    checked: int
    mismatched: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def intact(self) -> bool:
        """True when every file listed in the digest is present and unchanged."""
        return not self.mismatched and not self.missing


def verify_digest(digest: Mapping[str, Any], read_content: Callable[[str], bytes | None]) -> DigestResult:
    """Compare each listed file's hash with the file's uncompressed content.

    This checks the hashes only. The digest's own signature is checked by `aws cloudtrail validate-logs`, which is what
    `scripts/` runs against the real archive.
    """
    mismatched, missing = [], []
    entries = digest.get("logFiles", [])
    for entry in entries:
        content = read_content(entry["s3Object"])
        if content is None:
            missing.append(entry["s3Object"])
        elif hashlib.sha256(content).hexdigest() != entry["hashValue"].lower():
            mismatched.append(entry["s3Object"])
    return DigestResult(len(entries), tuple(mismatched), tuple(missing))
