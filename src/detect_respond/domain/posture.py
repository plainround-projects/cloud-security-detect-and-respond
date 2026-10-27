"""Posture findings: the baseline by severity, and the accepted risks with a reason."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")


@dataclass(frozen=True)
class Finding:
    """One failed control, from the posture service's finding format."""

    finding_id: str
    title: str
    severity: str
    resource: str

    @classmethod
    def from_asff(cls, raw: Mapping[str, Any]) -> Finding | None:
        """Parse a finding; None when it is not an open failure (passed, suppressed or resolved)."""
        if raw.get("Compliance", {}).get("Status") != "FAILED":
            return None
        if raw.get("Workflow", {}).get("Status") in {"SUPPRESSED", "RESOLVED"}:
            return None
        resources = raw.get("Resources") or [{}]
        return cls(raw["Id"], raw["Title"], raw["Severity"]["Label"], resources[0].get("Id", ""))


@dataclass(frozen=True)
class Acceptance:
    """A finding the owner has decided to live with, and why."""

    finding_id: str
    reason: str
    accepted_on: str


@dataclass(frozen=True)
class Baseline:
    """Open findings by severity at the start, after fixing, and how many of the rest are accepted with a reason."""

    start: Mapping[str, int]
    after_fixing: Mapping[str, int]
    accepted: Mapping[str, int]
    unaccepted_critical: tuple[str, ...]
    reasonless: tuple[str, ...]

    @property
    def meets_done_when(self) -> bool:
        """Every critical finding is resolved or accepted with a reason, and every acceptance has a reason."""
        return not self.unaccepted_critical and not self.reasonless


def _count(findings: Iterable[Finding]) -> dict[str, int]:
    counts = dict.fromkeys(SEVERITIES, 0)
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return counts


def baseline(start: Iterable[Finding], after: Iterable[Finding], acceptances: Iterable[Acceptance]) -> Baseline:
    """Compare the findings before and after fixing. An accepted finding counts as accepted, not as open."""
    starting, remaining = list(start), list(after)
    accepted_ids = {a.finding_id: a for a in acceptances}
    reasoned = {fid for fid, a in accepted_ids.items() if a.reason.strip()}
    open_after = [f for f in remaining if f.finding_id not in reasoned]
    accepted = [f for f in remaining if f.finding_id in reasoned]
    critical = tuple(f.finding_id for f in open_after if f.severity == "CRITICAL")
    reasonless = tuple(sorted(fid for fid, a in accepted_ids.items() if not a.reason.strip()))
    return Baseline(_count(starting), _count(open_after), _count(accepted), critical, reasonless)
