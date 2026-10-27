#!/usr/bin/env bash
# Step 6: remove the temporary exception and delete the workload account's resources, then write the time down. The archive in
# the security account cannot be deleted until its Object Lock retention (one day) and the lifecycle expiry (two days) have
# passed: run `10-teardown.sh archive` after that. Run it even if a step failed.
source "$(dirname "$0")/lib.sh"
require terraform
if [[ "${1:-}" == "archive" ]]; then
  use_account security
  "$TF" -chdir="$SECURITY_ENV" destroy -input=false -auto-approve
  rm -f "${SECURITY_ENV}/sandbox.auto.tfvars"
  log "archive destroyed"
  exit 0
fi

use_account workload
log "removing the drill key and profile first"
for key in $(aws iam list-access-keys --user-name "$DRILL_USER" --query 'AccessKeyMetadata[].AccessKeyId' --output text 2>/dev/null); do
  aws iam delete-access-key --user-name "$DRILL_USER" --access-key-id "$key"
done
for key in $(aws iam list-access-keys --user-name honeytoken-svc --query 'AccessKeyMetadata[].AccessKeyId' --output text 2>/dev/null); do
  aws iam delete-access-key --user-name honeytoken-svc --access-key-id "$key"
done
aws configure set aws_access_key_id "" --profile drill && aws configure set aws_secret_access_key "" --profile drill || true

"$TF" -chdir="$WORKLOAD_ENV" destroy -input=false -auto-approve
rm -f "${WORKLOAD_ENV}/sandbox.auto.tfvars"
echo "EXCEPTION REMOVED AT $(stamp)" | tee -a "${EVIDENCE_DIR}/containment.txt"
log "what still carries the project tag:"
aws resourcegroupstaggingapi get-resources --region "$REGION" --tag-filters Key=project,Values=detect-and-respond \
  --query 'ResourceTagMappingList[].ResourceARN' --output text || true
log "the security account's archive remains until its retention ends; then run: scripts/10-teardown.sh archive"
log "check the bill tomorrow: Config, Security Hub and keys cost money while they exist."
