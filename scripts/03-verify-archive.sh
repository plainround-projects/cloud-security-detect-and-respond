#!/usr/bin/env bash
# Step 1 "Done when": an action in the workload account appears in the central store within minutes, and an administrator of the
# workload account cannot delete or alter the log. Also checks the digest signatures with the provider's own validator.
source "$(dirname "$0")/lib.sh"
mkdir -p "$EVIDENCE_DIR"
bucket="$(archive_bucket)"

use_account workload
marker="archive-check-$(date -u +%s)"
log "an action in the workload account: create and delete a tagged placeholder topic (${marker})"
topic="$(aws sns create-topic --name "$marker" --region "$REGION" --query TopicArn --output text)"
aws sns delete-topic --topic-arn "$topic" --region "$REGION"

use_account security
log "waiting for the log file to reach the archive (5 to 15 minutes); polling every 60 seconds for up to 20"
for attempt in $(seq 1 20); do
  if aws s3 ls "s3://${bucket}/AWSLogs/${WORKLOAD_ACCOUNT_ID}/CloudTrail/" --recursive | tee "${EVIDENCE_DIR}/archive-listing.txt" | grep -q .; then
    log "the archive holds log files:"; sed -n '1,5p' "${EVIDENCE_DIR}/archive-listing.txt"; break
  fi
  log "nothing yet (attempt ${attempt} of 20)"; sleep 60
done
key="$(awk '{print $4}' "${EVIDENCE_DIR}/archive-listing.txt" | sed -n '1p')"
[[ -n "$key" ]] || die "no log file arrived; check aws cloudtrail get-trail-status in the workload account"

log "an administrator of the security account tries to delete a log file: this must be refused (policy deny and Object Lock)"
version="$(aws s3api list-object-versions --bucket "$bucket" --prefix "$key" --query 'Versions[0].VersionId' --output text)"
if aws s3api delete-object --bucket "$bucket" --key "$key" --version-id "$version" 2>&1 | tee "${EVIDENCE_DIR}/delete-by-security-admin.txt"; then
  grep -q AccessDenied "${EVIDENCE_DIR}/delete-by-security-admin.txt" || die "the delete was not refused"
fi

use_account workload
log "an administrator of the workload account tries the same: it has no rights in the security account at all"
if aws s3api delete-object --bucket "$bucket" --key "$key" 2>&1 | tee "${EVIDENCE_DIR}/delete-by-workload-admin.txt"; then
  grep -q AccessDenied "${EVIDENCE_DIR}/delete-by-workload-admin.txt" || die "the delete was not refused"
fi

log "log file validation with the provider's validator (checks the signatures that verify-archive cannot)"
aws cloudtrail validate-logs --trail-arn "arn:aws:cloudtrail:${REGION}:${WORKLOAD_ACCOUNT_ID}:trail/central-trail" \
  --start-time "$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)" \
  | tee "${EVIDENCE_DIR}/validate-logs.txt"
log "Next: scripts/04-drill-setup.sh"
