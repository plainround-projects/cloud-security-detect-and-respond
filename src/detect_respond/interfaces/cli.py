"""Command line for the detection and response work."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from detect_respond.application.use_cases import contain, posture_baseline, run_drill, scan_logs, verify_archive
from detect_respond.domain.errors import DetectRespondError
from detect_respond.domain.events import parse_time
from detect_respond.infrastructure.boto_revoker import BotoRevoker
from detect_respond.infrastructure.files import DetectionDirectory, PostureFiles
from detect_respond.infrastructure.log_archive import DirectoryArchive
from detect_respond.infrastructure.plan_audit import audit_rules
from detect_respond.interfaces import render


class SystemClock:
    """The wall clock."""

    def now(self) -> datetime:
        """The current time, timezone aware."""
        return datetime.now(UTC)


def _add_drill_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--archive", type=Path, required=True, help="folder synced from the central log bucket")
    parser.add_argument("--detections", type=Path, default=Path("detections"))
    parser.add_argument("--role", default="drill-broad-role")
    parser.add_argument("--session", default="intruder", help="the attacker's role session name")
    parser.add_argument("--user", default="drill-user")
    parser.add_argument(
        "--alerts", type=Path, help='when each alert reached you: {"alerts": [{"eventId": ..., "receivedAt": ...}]}'
    )


def build_parser() -> argparse.ArgumentParser:
    """The argument parser, kept separate so tests can drive it."""
    parser = argparse.ArgumentParser(prog="detect-respond", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    scan = commands.add_parser("scan", help="run every detection over the archive and print the alerts")
    scan.add_argument("--archive", type=Path, required=True)
    scan.add_argument("--detections", type=Path, default=Path("detections"))
    scan.add_argument("--honeytoken-key-id", help="access key id of the honeytoken, for detection D5")
    scan.add_argument("--expect", help="comma-separated detection ids that must fire; exit 1 otherwise")

    drill = commands.add_parser(
        "drill", help="rebuild the timeline from the archive and measure time to detect and to contain"
    )
    _add_drill_arguments(drill)

    review = commands.add_parser("review", help="write or verify the blameless review of a drill")
    _add_drill_arguments(review)
    target = review.add_mutually_exclusive_group(required=True)
    target.add_argument("--output", type=Path)
    target.add_argument("--check", type=Path)

    stop = commands.add_parser("contain", help="revoke a role's sessions and a user's keys (a dry run unless --apply)")
    stop.add_argument("--role", default="drill-broad-role")
    stop.add_argument("--user", default="drill-user")
    stop.add_argument(
        "--access-key-id", action="append", default=[], help="key to deactivate; default: all the user's keys"
    )
    stop.add_argument("--apply", action="store_true", help="do it; without this flag nothing in the account changes")

    verify = commands.add_parser("verify-archive", help="check the log files against the digest files")
    verify.add_argument("--archive", type=Path, required=True)

    posture = commands.add_parser("posture", help="the findings baseline and the accepted risks")
    posture.add_argument("--findings", type=Path, required=True, help="folder with the findings files")
    posture.add_argument("--before", default="before.json")
    posture.add_argument("--after", default="after.json")
    posture.add_argument("--accepted", type=Path, required=True)

    audit = commands.add_parser("audit-rules", help="check that the plan deploys exactly the detections in detections/")
    audit.add_argument("--plan", type=Path, required=True)
    audit.add_argument("--detections", type=Path, default=Path("detections"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one command; exit 0 on success, 1 when a check failed, 2 on bad input."""
    args = build_parser().parse_args(argv)
    try:
        handler = {
            "scan": _scan,
            "drill": _drill,
            "review": _review,
            "contain": _contain,
            "verify-archive": _verify,
            "posture": _posture,
            "audit-rules": _audit,
        }[args.command]
        return handler(args)
    except (DetectRespondError, OSError, ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


def _scan(args: argparse.Namespace) -> int:
    parameters = {"__HONEYTOKEN_ACCESS_KEY_ID__": args.honeytoken_key_id} if args.honeytoken_key_id else {}
    alerts = scan_logs(DirectoryArchive(args.archive), DetectionDirectory(args.detections), parameters)
    print(render.alert_blocks(alerts))
    fired = sorted({alert.detection.detection_id for alert in alerts})
    print(f"\n{len(alerts)} alerts from detections: {', '.join(fired) or 'none'}")
    missing = sorted(set(filter(None, (args.expect or "").split(","))) - set(fired))
    if missing:
        print(f"expected but did not fire: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0


def _alert_times(path: Path | None) -> dict[str, datetime]:
    if path is None:
        return {}
    return {
        item["eventId"]: parse_time(item["receivedAt"])
        for item in json.loads(path.read_text(encoding="utf-8"))["alerts"]
    }


def _run(args: argparse.Namespace):  # type: ignore[no-untyped-def]
    catalog = DetectionDirectory(args.detections)
    return run_drill(
        DirectoryArchive(args.archive), catalog, args.role, args.session, args.user, _alert_times(args.alerts)
    ), catalog


def _drill(args: argparse.Namespace) -> int:
    drill, _ = _run(args)
    print("\n".join(render.timeline_line(entry) for entry in drill.timeline))
    print()
    print("\n".join(render.measure_lines(drill.measured)))
    return 0 if drill.measured.time_to_contain is not None else 1


def _review(args: argparse.Namespace) -> int:
    drill, catalog = _run(args)
    text = render.review_markdown(drill, {d.detection_id: (d.title, d.prevention) for d in catalog.detections()})
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"wrote {args.output}")
        return 0
    if args.check.read_text(encoding="utf-8") != text:
        print(f"{args.check} is out of date: run `make review`", file=sys.stderr)
        return 1
    print(f"{args.check} is current")
    return 0


def _contain(args: argparse.Namespace) -> int:
    result = contain(BotoRevoker(), SystemClock(), args.role, args.user, tuple(args.access_key_id), apply=args.apply)
    print(("applied" if result.applied else "dry run, nothing changed; to do it, add --apply") + ":")
    print("\n".join(result.plan.cli_commands()))
    return 0


def _verify(args: argparse.Namespace) -> int:
    results = verify_archive(DirectoryArchive(args.archive))
    print("\n".join(render.archive_lines(results)))
    if not results:
        print("no digest files found", file=sys.stderr)
        return 1
    intact = all(result.intact for result in results)
    print("every logged file matches its digest" if intact else "the archive does not match its digests")
    return 0 if intact else 1


def _posture(args: argparse.Namespace) -> int:
    result = posture_baseline(PostureFiles(args.findings, args.accepted), args.before, args.after)
    print("\n".join(render.posture_lines(result)))
    for finding_id in result.unaccepted_critical:
        print(f"critical and neither fixed nor accepted: {finding_id}", file=sys.stderr)
    for finding_id in result.reasonless:
        print(f"accepted without a reason: {finding_id}", file=sys.stderr)
    return 0 if result.meets_done_when else 1


def _audit(args: argparse.Namespace) -> int:
    problems = audit_rules(args.plan, DetectionDirectory(args.detections).detections())
    for problem in problems:
        print(f"problem: {problem}")
    print("the plan deploys exactly the detections in detections/" if not problems else f"{len(problems)} problems")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
