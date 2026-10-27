#!/usr/bin/env bash
# Step 5, the responder's half: contain from the evidence. Without --apply it only prints what it would do.
# It denies every session of the role issued before now AND deactivates the user's keys; revoking only the key leaves the
# role's sessions alive until they expire.
source "$(dirname "$0")/lib.sh"
mkdir -p "$EVIDENCE_DIR"
use_account workload
mode=("$@")
"$PY" -m detect_respond contain --role "$DRILL_ROLE" --user "$DRILL_USER" "${mode[@]}" | tee -a "${EVIDENCE_DIR}/containment.txt"
if [[ "${mode[*]}" == *--apply* ]]; then
  echo "CONTAINED AT $(stamp)" | tee -a "${EVIDENCE_DIR}/containment.txt"
  log "to prove it, run the attacker's next call (the profile and session from 07-drill-attack.sh) and see AccessDenied"
fi
