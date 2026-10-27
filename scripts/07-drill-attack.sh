#!/usr/bin/env bash
# Step 5 of the lesson, the attacker's half. It runs ONLY against the drill resources in your own sandbox: it refuses unless
# the account is the workload account and the targets are the drill user, the drill role and the drill bucket. Write down the
# clock time it prints first: time to detect and time to contain are measured from it.
source "$(dirname "$0")/lib.sh"
mkdir -p "$EVIDENCE_DIR"
use_account workload
bucket="drill-data-${ACCOUNT}"
aws s3api head-bucket --bucket "$bucket" >/dev/null 2>&1 || die "the drill bucket ${bucket} does not exist; run 04-drill-setup.sh"

echo "FIRST ATTACKER ACTION AT $(stamp)" | tee "${EVIDENCE_DIR}/first-action.txt"
export AWS_PROFILE=drill
read -r ak sk st < <(aws sts assume-role --role-arn "arn:aws:iam::${ACCOUNT}:role/${DRILL_ROLE}" --role-session-name "$SESSION_NAME" \
  --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' --output text)
as_role() { AWS_PROFILE='' AWS_ACCESS_KEY_ID="$ak" AWS_SECRET_ACCESS_KEY="$sk" AWS_SESSION_TOKEN="$st" "$@"; }

log "look around";                  as_role aws s3 ls >/dev/null
log "D1: a new key for ${DRILL_USER}"; as_role aws iam create-access-key --user-name "$DRILL_USER" --query 'AccessKey.AccessKeyId' --output text >/dev/null
log "D2: the drill bucket made public"; as_role aws s3api put-bucket-acl --bucket "$bucket" --acl public-read
log "D4: a call in a Region the account does not use"; as_role aws ec2 describe-instances --region ap-southeast-2 >/dev/null
echo "LAST ATTACKER ACTION AT $(stamp)" | tee -a "${EVIDENCE_DIR}/first-action.txt"
log "the credentials stay in this shell only. Now be the responder: read your email, then scripts/08-contain.sh"
printf '%s\n' "$ak" > "${EVIDENCE_DIR}/.session-key-id"
unset sk st
