#!/usr/bin/env bash
# Step 1 of the lesson, security account: the tamper-resistant archive (encrypted, versioned, Object Lock in compliance
# mode, deletes denied). Needs SECURITY_PROFILE, SECURITY_ACCOUNT_ID, WORKLOAD_ACCOUNT_ID.
# Retention is one day and cannot be shortened by anyone: the files and the bucket stay until it ends (see 10-teardown.sh).
source "$(dirname "$0")/lib.sh"
require terraform
: "${WORKLOAD_ACCOUNT_ID:?set WORKLOAD_ACCOUNT_ID}"
use_account security

cat > "${SECURITY_ENV}/sandbox.auto.tfvars" <<TFVARS
security_account_id = "${ACCOUNT}"
workload_account_id = "${WORKLOAD_ACCOUNT_ID}"
retention_days      = 1
expire_days         = 2
TFVARS

log "deploying the archive into the security account ${ACCOUNT}"
"$TF" -chdir="$SECURITY_ENV" init -input=false
"$TF" -chdir="$SECURITY_ENV" apply -input=false -auto-approve
log "archive bucket: $("$TF" -chdir="$SECURITY_ENV" output -raw log_bucket_name). Next: scripts/02-deploy-workload.sh"
