#!/usr/bin/env bash
# Stretch goal: a honeytoken, a credential that should never be used. Creates its key, deploys detection D5 for that key id,
# then uses the key once so you see the alert. The secret half of the key is discarded at once.
source "$(dirname "$0")/lib.sh"
require terraform
use_account workload
key_id="$(aws iam create-access-key --user-name honeytoken-svc --query 'AccessKey.AccessKeyId' --output text)"
log "honeytoken key id ${key_id}; deploying D5 for it"
printf 'honeytoken_access_key_id = "%s"\n' "$key_id" >> "${WORKLOAD_ENV}/sandbox.auto.tfvars"
"$TF" -chdir="$WORKLOAD_ENV" apply -input=false -auto-approve
log "the alert for any use of this key arrives by email; to see one, sign a call with it (you need the secret, which this script did not keep)."
log "offline, the same detection is replayed by: .venv/bin/python -m detect_respond scan --archive <logs> --honeytoken-key-id ${key_id}"
