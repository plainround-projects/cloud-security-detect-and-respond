#!/usr/bin/env bash
# Step 4 of the lesson: plant the weakness (a deliberate, temporary exception) and write down what the credential can do
# BEFORE the drill. The drill user's key is created here, kept only in the AWS CLI profile "drill", and never printed.
source "$(dirname "$0")/lib.sh"
require terraform
mkdir -p "$EVIDENCE_DIR"
use_account workload

sed -i.bak 's/^enable_drill .*/enable_drill        = true/' "${WORKLOAD_ENV}/sandbox.auto.tfvars" && rm -f "${WORKLOAD_ENV}/sandbox.auto.tfvars.bak"
log "TEMPORARY EXCEPTION: creating ${DRILL_USER}, ${DRILL_ROLE} (PowerUserAccess) and a public-capable drill bucket"
"$TF" -chdir="$WORKLOAD_ENV" apply -input=false -auto-approve

if [[ -z "$(aws iam list-access-keys --user-name "$DRILL_USER" --query 'AccessKeyMetadata[0].AccessKeyId' --output text | grep -v None || true)" ]]; then
  read -r key_id secret < <(aws iam create-access-key --user-name "$DRILL_USER" --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text)
  aws configure set aws_access_key_id "$key_id" --profile drill
  aws configure set aws_secret_access_key "$secret" --profile drill
  aws configure set region "$REGION" --profile drill
  unset secret
  log "the drill key is in the AWS CLI profile 'drill' (id ${key_id}); delete it with scripts/10-teardown.sh"
fi

{
  echo "What ${DRILL_ROLE} can do, written down before the drill ($(stamp)):"
  aws iam list-attached-role-policies --role-name "$DRILL_ROLE" --output text
  aws iam list-role-policies --role-name "$DRILL_ROLE" --output text
  echo "What ${DRILL_USER} can do directly:"
  aws iam list-user-policies --user-name "$DRILL_USER" --output text
} | tee "${EVIDENCE_DIR}/drill-capabilities.txt"
log "success test, decided now: the responder identifies every attacker action from the logs and stops the next call. Next: scripts/05-posture-baseline.sh"
