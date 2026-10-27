#!/usr/bin/env bash
# Step 3 of the lesson: record the posture baseline, then (after you fix what matters) the second reading.
# Usage: 05-posture-baseline.sh before    # right after deploy, writes evidence/posture/before.json
#        05-posture-baseline.sh after     # after fixing, writes after.json and prints the table
# Accept a risk by adding it, with a reason, to docs/posture-acceptances.json.
source "$(dirname "$0")/lib.sh"
phase="${1:-before}"
use_account workload
mkdir -p "${EVIDENCE_DIR}/posture"
log "reading open findings from the posture service (the first full scan takes minutes to hours)"
aws securityhub get-findings --region "$REGION" --max-items 1000 \
  --filters '{"ComplianceStatus":[{"Value":"FAILED","Comparison":"EQUALS"}],"WorkflowStatus":[{"Value":"NEW","Comparison":"EQUALS"},{"Value":"NOTIFIED","Comparison":"EQUALS"}],"RecordState":[{"Value":"ACTIVE","Comparison":"EQUALS"}]}' \
  | tee "${EVIDENCE_DIR}/posture/${phase}.json" | python3 -c 'import json, sys; print(len(json.load(sys.stdin)["Findings"]), "open findings")'
if [[ "$phase" == "after" ]]; then
  "$PY" -m detect_respond posture --findings "${EVIDENCE_DIR}/posture" --accepted "${ROOT}/docs/posture-acceptances.json"
fi
