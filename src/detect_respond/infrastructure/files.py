"""Detections, the alert template, posture findings and accepted risks, read from files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from detect_respond.domain.detections import Detection
from detect_respond.domain.errors import InvalidDetectionError
from detect_respond.domain.posture import Acceptance, Finding


class DetectionDirectory:
    """A `DetectionCatalog` over the `detections/` folder: one JSON file per detection and `alert-template.txt`."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def detections(self) -> tuple[Detection, ...]:
        """Load and validate every `d*.json`, ordered by id; ids must be unique."""
        found = [
            Detection.from_mapping(json.loads(p.read_text(encoding="utf-8")))
            for p in sorted(self._root.glob("d*.json"))
        ]
        ids = [d.detection_id for d in found]
        if not found or len(ids) != len(set(ids)):
            raise InvalidDetectionError(f"{self._root} must hold detection files with unique ids")
        return tuple(sorted(found, key=lambda d: d.detection_id))

    def template(self) -> str:
        """The alert template."""
        return (self._root / "alert-template.txt").read_text(encoding="utf-8")


class PostureFiles:
    """A `PostureSource` over findings files (`{"Findings": [...]}`, as `get-findings` prints them) and acceptances."""

    def __init__(self, folder: Path, acceptances: Path) -> None:
        self._folder = folder
        self._acceptances = acceptances

    def findings(self, name: str) -> tuple[Finding, ...]:
        """Open failed findings from one file."""
        raw: dict[str, Any] = json.loads((self._folder / name).read_text(encoding="utf-8"))
        parsed = (Finding.from_asff(item) for item in raw["Findings"])
        return tuple(finding for finding in parsed if finding is not None)

    def acceptances(self) -> tuple[Acceptance, ...]:
        """The accepted risks."""
        raw = json.loads(self._acceptances.read_text(encoding="utf-8"))
        return tuple(Acceptance(a["findingId"], a.get("reason", ""), a.get("acceptedOn", "")) for a in raw["accepted"])
