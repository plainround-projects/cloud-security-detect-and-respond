#!/usr/bin/env bash
# Steps 5 and 6: copy the archive out of the security account, check it was not altered, rebuild the timeline from the logs
# alone, measure time to detect and time to contain, and write the blameless review. Put the times your alerts reached you in
# evidence/alerts.json ({"alerts": [{"eventId": "...", "receivedAt": "2026-10-22T11:03:42Z"}]}) to measure real latency; without
# it the event time is used, which is the lower bound.
source "$(dirname "$0")/lib.sh"
mkdir -p "${EVIDENCE_DIR}/archive"
use_account security
log "syncing the archive (events can lag by 5 to 15 minutes)"
aws s3 sync "s3://$(archive_bucket)/AWSLogs/" "${EVIDENCE_DIR}/archive/AWSLogs/" --only-show-errors
"$PY" -m detect_respond verify-archive --archive "${EVIDENCE_DIR}/archive"
alerts=()
[[ -f "${EVIDENCE_DIR}/alerts.json" ]] && alerts=(--alerts "${EVIDENCE_DIR}/alerts.json")
"$PY" -m detect_respond scan --archive "${EVIDENCE_DIR}/archive" --expect D1,D2,D4 | tail -n 1
"$PY" -m detect_respond drill --archive "${EVIDENCE_DIR}/archive" ${alerts[@]+"${alerts[@]}"} | tee "${EVIDENCE_DIR}/timeline.txt"
"$PY" -m detect_respond review --archive "${EVIDENCE_DIR}/archive" ${alerts[@]+"${alerts[@]}"} --output "${EVIDENCE_DIR}/REVIEW.md"
log "the review is ${EVIDENCE_DIR}/REVIEW.md. Edit its wording if you like, but keep an event id on every claim."
