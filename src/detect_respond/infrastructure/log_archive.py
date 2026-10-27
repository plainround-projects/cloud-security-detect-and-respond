"""The central log archive, read from a folder synced out of the archive bucket (plain or gzip JSON)."""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from detect_respond.domain.errors import InvalidLogError
from detect_respond.domain.events import AuditEvent

DIGEST_FOLDER = "CloudTrail-Digest"


def _load(path: Path) -> Any:
    opener = gzip.open if path.suffix == ".gz" else open
    try:
        with opener(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise InvalidLogError(f"{path} cannot be read as a JSON log file: {error}") from error


class DirectoryArchive:
    """A `LogArchive` over a folder. Digest files live under a `CloudTrail-Digest` folder, as in the real bucket."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def _files(self, *, digests: bool) -> list[Path]:
        found = sorted(p for p in self._root.rglob("*") if p.is_file() and p.suffix in {".json", ".gz"})
        return [p for p in found if (DIGEST_FOLDER in p.parts) == digests]

    def events(self) -> Iterable[AuditEvent]:
        """Every record of every log file, in file order."""
        records: list[Mapping[str, Any]] = []
        for path in self._files(digests=False):
            decoded = _load(path)
            records += decoded if isinstance(decoded, list) else decoded.get("Records") or decoded.get("Events") or []
        return [AuditEvent.from_record(record) for record in records]

    def digests(self) -> Iterable[Mapping[str, Any]]:
        """Every digest file."""
        return [_load(path) for path in self._files(digests=True)]

    def read_log(self, s3_object: str) -> bytes | None:
        """The uncompressed bytes of a log file named as the digest names it (a key relative to the archive root)."""
        path = self._root / s3_object
        if not path.is_file():
            return None
        return gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
