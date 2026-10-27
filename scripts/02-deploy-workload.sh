#!/usr/bin/env bash
# Steps 1 to 3 of the lesson, workload account: the multi-region trail into the archive, the detections D1 to D4 in each
# Region that needs them, alerting by email, posture management and a budget.
# Needs WORKLOAD_PROFILE, WORKLOAD_ACCOUNT_ID, SECURITY_ACCOUNT_ID, ALERT_EMAIL. Run 01-deploy-security.sh first.
source "$(dirname "$0")/lib.sh"
require terraform
: "${ALERT_EMAIL:?set ALERT_EMAIL for the alerts and the budget notices}"
: "${SECURITY_ACCOUNT_ID:?set SECURITY_ACCOUNT_ID}"
use_account workload

cat > "${WORKLOAD_ENV}/sandbox.auto.tfvars" <<TFVARS
workload_account_id = "${ACCOUNT}"
log_bucket_name     = "$("$TF" -chdir="$SECURITY_ENV" output -raw log_bucket_name)"
log_key_arn         = "$("$TF" -chdir="$SECURITY_ENV" output -raw log_key_arn)"
alert_email         = "${ALERT_EMAIL}"
force_destroy       = true
enable_drill        = false
TFVARS

log "deploying the trail and the detections into the workload account ${ACCOUNT}"
"$TF" -chdir="$WORKLOAD_ENV" init -input=false
"$TF" -chdir="$WORKLOAD_ENV" apply -input=false -auto-approve
log "three email subscriptions (one per Region) are pending: open each message from AWS Notifications and confirm it, or no alert reaches you."
log "Next: scripts/03-verify-archive.sh"
