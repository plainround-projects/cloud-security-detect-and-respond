#!/usr/bin/env bash
# shellcheck disable=SC2034
# Shared helpers for the runbook scripts. Sourced, never run on its own.
#
# Two accounts take part: the security account (owns the archive) and the workload account (the sandbox being watched).
# Each has its own AWS CLI profile. Set SECURITY_PROFILE, WORKLOAD_PROFILE, SECURITY_ACCOUNT_ID and WORKLOAD_ACCOUNT_ID.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE_DIR="${EVIDENCE_DIR:-${ROOT}/evidence}"
SECURITY_ENV="${ROOT}/infra/environments/security"
WORKLOAD_ENV="${ROOT}/infra/environments/workload"
REGION="${AWS_REGION:-eu-west-1}"
TF="${TF:-terraform}"
PY="${ROOT}/.venv/bin/python"
DRILL_ROLE="drill-broad-role"
DRILL_USER="drill-user"
SESSION_NAME="intruder"

log() { printf '%s %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

require() {
  for tool in "$@"; do command -v "$tool" >/dev/null 2>&1 || die "$tool is required"; done
}

# use_account security|workload: point the AWS CLI and Terraform at one account and refuse any other.
use_account() {
  require aws
  local which="$1" profile_var expected_var identity arn
  case "$which" in
    security) profile_var=SECURITY_PROFILE; expected_var=SECURITY_ACCOUNT_ID ;;
    workload) profile_var=WORKLOAD_PROFILE; expected_var=WORKLOAD_ACCOUNT_ID ;;
    *) die "unknown account $which" ;;
  esac
  [[ -n "${!profile_var:-}" ]] || die "set ${profile_var} to the AWS CLI profile of the ${which} account"
  [[ -n "${!expected_var:-}" ]] || die "set ${expected_var} to the 12-digit id of the ${which} account"
  export AWS_PROFILE="${!profile_var}"
  identity="$(aws sts get-caller-identity --query '[Account,Arn]' --output text)"
  ACCOUNT="${identity%%$'\t'*}"
  arn="${identity##*$'\t'}"
  [[ "$ACCOUNT" == "${!expected_var}" ]] || die "profile ${AWS_PROFILE} is account ${ACCOUNT}, not ${!expected_var}"
  [[ "$arn" != *":root" ]] || die "do not run this as the account root user; use an administrator role or user"
  export ACCOUNT
}

archive_bucket() { echo "detect-archive-${SECURITY_ACCOUNT_ID}"; }

stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
