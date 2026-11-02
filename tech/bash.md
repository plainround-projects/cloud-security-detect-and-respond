# Bash

## What it is

Bash is a **shell**: a program that reads commands you type (or that a file contains) and runs them. A **shell script** is a text file of such commands. Each command starts a program, such as `aws` or `grep`, and passes it options. This repository's scripts are written for **Bash** (they start with `#!/usr/bin/env bash`), verified with Bash 5.3 on macOS. Section "Mistakes people make" explains one construct that does not run on the old Bash 3.2 that Apple ships in `/bin/bash`.

## Why this repository uses it

The drill needs a person at a keyboard in two accounts: deploy the archive, deploy the workload, check the archive, plant the weakness, attack, contain, collect, tear down. These steps are best shown as the exact commands to type, so they live in `scripts/` as Bash, and use the AWS command-line tool ([aws-cli.md](aws-cli.md)). Nothing here is run in CI or by `make validate`; the offline replay (`make demo-drill`) covers the logic, and the scripts are for the day you have two sandbox accounts.

## Where it appears

| Path | What it does |
| --- | --- |
| `scripts/lib.sh` | shared helpers: logging, `require`, `use_account`; sourced by the others |
| `scripts/01-deploy-security.sh`, `02-deploy-workload.sh` | write the variables file and run Terraform apply in each account |
| `scripts/03-verify-archive.sh` | an action in the workload account, the archive fills, deletes are refused |
| `scripts/04-drill-setup.sh` | switches the drill on and records what the credential can do |
| `scripts/05-posture-baseline.sh` | reads the posture findings, before or after fixing |
| `scripts/06-honeytoken.sh` | creates the bait key and deploys detection D5 for it |
| `scripts/07-drill-attack.sh` | the attacker's half of the drill |
| `scripts/08-contain.sh` | the responder's half, a dry run unless told otherwise |
| `scripts/09-collect-and-measure.sh` | copies the archive out, verifies it, measures, writes the review |
| `scripts/10-teardown.sh` | removes the exception and the workload account's resources |
| `Makefile` | calls these through `make up`, `run`, `attack`, `respond`, `measure`, `down` |

## How it works underneath

When you run `scripts/01-deploy-security.sh`, the kernel sees the first line, `#!/usr/bin/env bash`, and starts Bash with the script as input. Bash reads one command at a time. For each command it expands things first (variables, `$(...)`, wildcards), splits the result into words, then starts the program with those words as its **arguments**. Every program ends with an **exit code**: 0 means success, anything else means failure. `$?` holds the last exit code. A **pipe** (`a | b`) connects the output of `a` to the input of `b`. `>file` sends output to a file; `2>&1` sends error output to the same place as normal output. **Environment variables** are text values handed to every child program.

## Walkthrough of this repository's use

Every shell script in the repository is shown below, line by line, in the order the runbook uses them. Read this section first, because the same ideas appear on almost every line.

**A shell and a script.** A **shell** is a program that reads a line of text, treats the first word as the name of a program, treats the rest as that program's **arguments**, runs it, waits for it to finish, and then reads the next line. Bash is one shell. A **script** is a text file of such lines. A **process** is one running program; when a script runs a command, the shell starts a new process for it. When a process ends it returns a number called its **exit code**: `0` means success and any other number means failure. The shell remembers the last exit code in `$?`, and the flow control in a script (`if`, `&&`, `||`) is decided by exit codes.

**Variables and quoting.** `NAME=value` stores text (there must be no spaces around `=`). `$NAME` or `${NAME}` pastes it back. **Environment variables** are variables that are copied to every program the script starts; `export NAME` makes a variable one of them. Double quotes (`"..."`) keep a value as **one word** even if it contains spaces or wildcard characters, while still pasting variables inside them; single quotes (`'...'`) paste nothing and keep every character literally. An unquoted `$NAME` that holds `a b` becomes two arguments, which is a classic source of bugs, so the scripts quote almost everything.

**Command substitution, pipes and redirection.** `$(command)` runs the command and pastes its output. A **pipe**, `a | b`, sends the output of `a` into the input of `b`. `> file` sends output into a file (replacing it), `>> file` appends, `< file` reads a file as input, and `2>&1` sends the error output to the same place as the normal output. `/dev/null` is a special file that throws away everything written to it. `&&` runs the next command only if the previous one succeeded; `||` runs it only if the previous one failed.

**Functions and files.** `name() { ...; }` defines a **function**, a named group of commands; its arguments are `$1` (the first), `$2` (the second), `$3` (the third) up to `$9`, and `"$@"` is all of them, each kept as a separate word. `source file` runs another file's commands inside the current shell, so that its functions and variables become available; that is how the numbered scripts use `lib.sh`. A line that starts with `#!` on the very first line (the **shebang**) tells the operating system which program should run the file; `#!/usr/bin/env bash` means "find `bash` on the search path". Any other line that starts with `#` is a **comment**, ignored by the shell.

### `scripts/lib.sh`: the shared helpers

This file is never run on its own. Every numbered script loads it with `source`, so the functions and variables defined here are available to all of them. Two AWS accounts take part in the drill (the **security account**, which owns the archive, and the **workload account**, the sandbox being watched) and each has its own AWS CLI profile.

From `scripts/lib.sh` (lines 1 to 7):

```bash
#!/usr/bin/env bash
# shellcheck disable=SC2034
# Shared helpers for the runbook scripts. Sourced, never run on its own.
#
# Two accounts take part: the security account (owns the archive) and the workload account (the sandbox being watched).
# Each has its own AWS CLI profile. Set SECURITY_PROFILE, WORKLOAD_PROFILE, SECURITY_ACCOUNT_ID and WORKLOAD_ACCOUNT_ID.
set -euo pipefail
```

`set -euo pipefail` switches on three safety options for the whole script (and for every script that `source`s this file). `-e` makes the script **stop at the first command that fails**, instead of carrying on and doing more damage. `-u` makes the use of an **unset variable** an error, so a typo such as `$BUKET` stops the script instead of silently becoming an empty string. `-o pipefail` makes a pipeline (`a | b | c`) fail if **any** part of it fails, not only the last. The `# shellcheck disable=SC2034` line is an instruction for the checker called ShellCheck ([shellcheck.md](shellcheck.md)): it says "do not warn that a variable looks unused", because the variables set here are used by the scripts that source this file.

The comment lines in between say that two accounts take part, and that the variables `SECURITY_PROFILE`, `WORKLOAD_PROFILE`, `SECURITY_ACCOUNT_ID` and `WORKLOAD_ACCOUNT_ID` must be set by the person.

From `scripts/lib.sh` (lines 9 to 10):

```bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE_DIR="${EVIDENCE_DIR:-${ROOT}/evidence}"
```

`ROOT=` finds the repository's top folder, wherever the script is started from. Reading it from the inside out: `${BASH_SOURCE[0]}` is the path of the file being run (an **array** variable; `[0]` is its first item); `dirname` removes the file name, leaving the folder; adding `/..` goes one folder up; `cd ... && pwd` changes into that folder and prints its absolute path; `$(...)` pastes that output; the outer quotes keep it as one word.

From `scripts/lib.sh` (lines 11 to 18):

```bash
SECURITY_ENV="${ROOT}/infra/environments/security"
WORKLOAD_ENV="${ROOT}/infra/environments/workload"
REGION="${AWS_REGION:-eu-west-1}"
TF="${TF:-terraform}"
PY="${ROOT}/.venv/bin/python"
DRILL_ROLE="drill-broad-role"
DRILL_USER="drill-user"
SESSION_NAME="intruder"
```

These lines define the names the scripts share. `SECURITY_ENV` and `WORKLOAD_ENV` are the two Terraform folders. `EVIDENCE_DIR` is where the scripts save proof, and `REGION` is the AWS region. 
`${NAME:-default}` means "the value of `NAME`, or `default` if `NAME` is unset or empty". So `REGION="${AWS_REGION:-eu-west-1}"` uses the region the person set, otherwise `eu-west-1`. `EVIDENCE_DIR` uses the same trick with another variable as the default.

`TF="${TF:-terraform}"` lets a person run OpenTofu instead of Terraform by setting `TF=tofu`. `PY` is the project's own Python in the virtual environment. `DRILL_ROLE`, `DRILL_USER` and `SESSION_NAME` are the names of the deliberately weak role, the user that can assume it and the session name the attacker will use (`intruder`), written once so that no script spells them twice.

From `scripts/lib.sh` (lines 20 to 21):

```bash
log() { printf '%s %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }
```

Two small functions that every script uses. `log` prints a message with a time stamp: `printf` is a print command that takes a **format** (`'%s %s\n'`: two text fields and a line break) and then the values; `$(date -u +%H:%M:%SZ)` is the current time in UTC as hours:minutes:seconds ([unix-tools.md](unix-tools.md)); `$*` is all the arguments joined by spaces. `die` prints `error: ` and the message to **standard error** (`>&2` sends the output to the error channel, which a person sees even when the normal output is redirected) and then runs `exit 1`, ending the whole script with a failure code.

From `scripts/lib.sh` (lines 23 to 25):

```bash
require() {
  for tool in "$@"; do command -v "$tool" >/dev/null 2>&1 || die "$tool is required"; done
}
```

`require` checks that programs are installed. `for tool in "$@"; do ...; done` is a **loop** that runs the commands once for each argument, with the variable `tool` set to it. `command -v "$tool"` prints where a program is if it exists and fails if not; `>/dev/null 2>&1` hides both its normal and its error output. `||` means "if that failed, then" and the next command, `die "$tool is required"`, stops the script with a clear message.

From `scripts/lib.sh` (lines 27 to 45):

```bash
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
```

The comment describes `use_account`: point the AWS CLI and Terraform at one of the two accounts and refuse any other.

- `require aws` stops if the AWS command-line tool is missing ([aws-cli.md](aws-cli.md)).
- `local which="$1" profile_var expected_var identity arn` names the argument (`security` or `workload`) and declares four more variables that exist only inside this function.
- The `case "$which" in ... esac` block chooses by the argument: `security) profile_var=SECURITY_PROFILE; expected_var=SECURITY_ACCOUNT_ID ;;` and the same for `workload`; `*) die "unknown account $which" ;;` catches anything else. Each branch ends with `;;`. The variables hold the **names** of other variables, not their values.
- `[[ -n "${!profile_var:-}" ]] || die ...` is a check that the profile variable is set. `${!profile_var}` is **indirect expansion**: if `profile_var` holds the text `SECURITY_PROFILE`, then `${!profile_var}` is the value of the variable `SECURITY_PROFILE`. `[[ ... ]]` is Bash's test command; `-n` is true when the text is not empty; the `:-` form keeps `set -u` quiet when the variable is unset. The next line does the same for the expected account number.
- `export AWS_PROFILE="${!profile_var}"` sets the environment variable that the AWS CLI reads to choose a profile (a named set of credentials). From now on every `aws` command in this script uses that account. `export` makes it visible to the programs the script starts.
- `identity="$(aws sts get-caller-identity --query '[Account,Arn]' --output text)"` asks AWS who the credentials belong to ([aws-sts.md](aws-sts.md)); the answer is the account number and the full name (ARN) of the identity, separated by a **tab**.
- `ACCOUNT="${identity%%$'\t'*}"` cuts at the tab: `%%` removes the **longest** match of the pattern from the **end** of the text (the pattern is "a tab and everything after it"; `$'\t'` is how Bash writes a tab), which leaves the account number. `arn="${identity##*$'\t'}"` removes the longest match from the **start**, leaving the ARN.
- `[[ "$ACCOUNT" == "${!expected_var}" ]] || die "profile ... is account ..., not ..."` stops if the profile belongs to another account than the one the person named. This is what stops the drill from being run in the wrong account.
- `[[ "$arn" != *":root" ]] || die ...` stops if the identity is the account's root user (an ARN that ends in `:root`). The pattern `*":root"` means "anything followed by :root".
- `export ACCOUNT` keeps the account number for the caller.

From `scripts/lib.sh` (line 47):

```bash
archive_bucket() { echo "detect-archive-${SECURITY_ACCOUNT_ID}"; }
```

`archive_bucket` is a one-line function that **builds a name**: `echo` prints the archive bucket's name, which contains the security account's number (bucket names must be unique across all of AWS). The caller captures it with `$(archive_bucket)`.

From `scripts/lib.sh` (line 49):

```bash
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
```

`stamp` prints the current time in UTC in the form `2026-10-22T11:03:42Z`: `date -u +%Y-%m-%dT%H:%M:%SZ` ([unix-tools.md](unix-tools.md)). It is used to write down the clock time of the attacker's first action and of containment, from which the two measured times are computed.

### `scripts/01-deploy-security.sh`: the archive

From `scripts/01-deploy-security.sh` (lines 1 to 4):

```bash
#!/usr/bin/env bash
# Step 1 of the lesson, security account: the tamper-resistant archive (encrypted, versioned, Object Lock in compliance
# mode, deletes denied). Needs SECURITY_PROFILE, SECURITY_ACCOUNT_ID, WORKLOAD_ACCOUNT_ID.
# Retention is one day and cannot be shortened by anyone: the files and the bucket stay until it ends (see 10-teardown.sh).
```

The comments explain: this is step 1, in the security account; the archive is tamper-resistant (encrypted, versioned, locked in compliance mode, deletes denied); it needs three variables; and the retention is one day and **cannot be shortened by anyone**, so the files and the bucket stay until it ends.

From `scripts/01-deploy-security.sh` (lines 5 to 8):

```bash
source "$(dirname "$0")/lib.sh"
require terraform
: "${WORKLOAD_ACCOUNT_ID:?set WORKLOAD_ACCOUNT_ID}"
use_account security
```

`source "$(dirname "$0")/lib.sh"` loads the helper file that sits next to this script. `$0` is the path this script was started with, `dirname` takes its folder, and `source` runs `lib.sh` inside the current shell, so `log`, `die`, `require` and the variables become available (and the `set -euo pipefail` of `lib.sh` applies here too).

- `require terraform` stops if Terraform is not installed.
- `: "${WORKLOAD_ACCOUNT_ID:?set WORKLOAD_ACCOUNT_ID}"` is a one-line "required variable" check. `:` is a command that does nothing, and its argument is expanded first; `${NAME:?message}` stops the script with the message if `NAME` is unset or empty.
- `use_account security` runs the account check for the security account.

From `scripts/01-deploy-security.sh` (lines 10 to 15):

```bash
cat > "${SECURITY_ENV}/sandbox.auto.tfvars" <<TFVARS
security_account_id = "${ACCOUNT}"
workload_account_id = "${WORKLOAD_ACCOUNT_ID}"
retention_days      = 1
expire_days         = 2
TFVARS
```

A **here-document**: `cat > FILE <<TFVARS` sends everything up to the line that contains only `TFVARS` into `cat`, which writes it into the file. The marker is not quoted, so the shell **substitutes the variables** inside. The file is a Terraform variables file ([terraform.md](terraform.md)); `.auto.tfvars` files are read automatically and `.gitignore` keeps this one out of git ([git.md](git.md)). `retention_days = 1` is how long the files are locked and `expire_days = 2` is when they are removed; the expiry must be longer than the retention.

From `scripts/01-deploy-security.sh` (lines 17 to 20):

```bash
log "deploying the archive into the security account ${ACCOUNT}"
"$TF" -chdir="$SECURITY_ENV" init -input=false
"$TF" -chdir="$SECURITY_ENV" apply -input=false -auto-approve
log "archive bucket: $("$TF" -chdir="$SECURITY_ENV" output -raw log_bucket_name). Next: scripts/02-deploy-workload.sh"
```

`init -input=false` prepares the folder (`-chdir` runs Terraform as if inside that folder; `-input=false` forbids questions). `apply -input=false -auto-approve` **creates the real resources**; `-auto-approve` skips the "type yes" prompt, which is acceptable because the script already proved it is in the right account. The last `log` prints the bucket's name, read with `"$TF" ... output -raw log_bucket_name` (`-raw` prints it without quotes), and names the next script.

### `scripts/02-deploy-workload.sh`: the trail, the detections, posture and the budget

From `scripts/02-deploy-workload.sh` (lines 1 to 4):

```bash
#!/usr/bin/env bash
# Steps 1 to 3 of the lesson, workload account: the multi-region trail into the archive, the detections D1 to D4 in each
# Region that needs them, alerting by email, posture management and a budget.
# Needs WORKLOAD_PROFILE, WORKLOAD_ACCOUNT_ID, SECURITY_ACCOUNT_ID, ALERT_EMAIL. Run 01-deploy-security.sh first.
```

The comments explain: this covers steps 1 to 3 in the workload account, the multi-region trail into the archive, detections D1 to D4 in each Region that needs them, alerting by email, posture management and a budget; it needs four variables; and the security deployment must be done first.

From `scripts/02-deploy-workload.sh` (lines 5 to 9):

```bash
source "$(dirname "$0")/lib.sh"
require terraform
: "${ALERT_EMAIL:?set ALERT_EMAIL for the alerts and the budget notices}"
: "${SECURITY_ACCOUNT_ID:?set SECURITY_ACCOUNT_ID}"
use_account workload
```

`source "$(dirname "$0")/lib.sh"` loads the helper file that sits next to this script. `$0` is the path this script was started with, `dirname` takes its folder, and `source` runs `lib.sh` inside the current shell, so `log`, `die`, `require` and the variables become available (and the `set -euo pipefail` of `lib.sh` applies here too).

`require terraform` stops if Terraform is missing. The two `: "${NAME:?message}"` lines stop the script unless `ALERT_EMAIL` and `SECURITY_ACCOUNT_ID` are set (`${NAME:?message}` fails with the message if the variable is unset or empty). `use_account workload` runs the account check for the workload account.

From `scripts/02-deploy-workload.sh` (lines 11 to 18):

```bash
cat > "${WORKLOAD_ENV}/sandbox.auto.tfvars" <<TFVARS
workload_account_id = "${ACCOUNT}"
log_bucket_name     = "$("$TF" -chdir="$SECURITY_ENV" output -raw log_bucket_name)"
log_key_arn         = "$("$TF" -chdir="$SECURITY_ENV" output -raw log_key_arn)"
alert_email         = "${ALERT_EMAIL}"
force_destroy       = true
enable_drill        = false
TFVARS
```

A here-document like the one in the previous script. This time three of the values come from the **other** environment: `$("$TF" -chdir="$SECURITY_ENV" output -raw log_bucket_name)` and `... log_key_arn` read the archive's bucket name and key ARN from the security environment's Terraform output, so the trail knows where to write. `alert_email` is where alerts and budget notices go, `force_destroy = true` lets the teardown delete buckets that contain objects, and `enable_drill = false` keeps the deliberate weakness switched off for now.

From `scripts/02-deploy-workload.sh` (lines 20 to 24):

```bash
log "deploying the trail and the detections into the workload account ${ACCOUNT}"
"$TF" -chdir="$WORKLOAD_ENV" init -input=false
"$TF" -chdir="$WORKLOAD_ENV" apply -input=false -auto-approve
log "three email subscriptions (one per Region) are pending: open each message from AWS Notifications and confirm it, or no alert reaches you."
log "Next: scripts/03-verify-archive.sh"
```

`init` and `apply` as before, in the workload environment. The two final `log` lines are important: the alert topics each have an **email subscription that stays pending** until the address confirms it by clicking the link in the message AWS sends, one per Region (three in all). Until that is done, **no alert reaches you**.

### `scripts/03-verify-archive.sh`: does the archive fill, and can it be altered?

From `scripts/03-verify-archive.sh` (lines 1 to 3):

```bash
#!/usr/bin/env bash
# Step 1 "Done when": an action in the workload account appears in the central store within minutes, and an administrator of the
# workload account cannot delete or alter the log. Also checks the digest signatures with the provider's own validator.
```

The comments explain the two "done when" tests of step 1: an action in the workload account appears in the central store within minutes, and an administrator of the workload account cannot delete or alter the log. It also checks the digest signatures with the provider's own validator.

From `scripts/03-verify-archive.sh` (lines 4 to 6):

```bash
source "$(dirname "$0")/lib.sh"
mkdir -p "$EVIDENCE_DIR"
bucket="$(archive_bucket)"
```

`source "$(dirname "$0")/lib.sh"` loads the helper file that sits next to this script. `$0` is the path this script was started with, `dirname` takes its folder, and `source` runs `lib.sh` inside the current shell, so `log`, `die`, `require` and the variables become available (and the `set -euo pipefail` of `lib.sh` applies here too).

`mkdir -p "$EVIDENCE_DIR"` makes the evidence folder (`-p`: also create parents, and do nothing if it exists). `bucket="$(archive_bucket)"` stores the archive bucket's name.

From `scripts/03-verify-archive.sh` (lines 8 to 12):

```bash
use_account workload
marker="archive-check-$(date -u +%s)"
log "an action in the workload account: create and delete a tagged placeholder topic (${marker})"
topic="$(aws sns create-topic --name "$marker" --region "$REGION" --query TopicArn --output text)"
aws sns delete-topic --topic-arn "$topic" --region "$REGION"
```

Work in the **workload** account: `use_account workload` points the AWS CLI at it. `marker="archive-check-$(date -u +%s)"` builds a unique name from the current time in seconds (`+%s`). The action itself is harmless: `aws sns create-topic` creates a notification topic with that name and prints its address (`--query TopicArn --output text`), then `aws sns delete-topic` deletes it. Both calls are recorded in the audit log, which is exactly what the script wants to see arrive in the archive.

From `scripts/03-verify-archive.sh` (lines 14 to 21):

```bash
use_account security
log "waiting for the log file to reach the archive (5 to 15 minutes); polling every 60 seconds for up to 20"
for attempt in $(seq 1 20); do
  if aws s3 ls "s3://${bucket}/AWSLogs/${WORKLOAD_ACCOUNT_ID}/CloudTrail/" --recursive | tee "${EVIDENCE_DIR}/archive-listing.txt" | grep -q .; then
    log "the archive holds log files:"; sed -n '1,5p' "${EVIDENCE_DIR}/archive-listing.txt"; break
  fi
  log "nothing yet (attempt ${attempt} of 20)"; sleep 60
done
```

Now work in the **security** account. The loop (`for attempt in $(seq 1 20); do`) tries up to 20 times, once a minute. Each pass runs `aws s3 ls "s3://${bucket}/AWSLogs/${WORKLOAD_ACCOUNT_ID}/CloudTrail/" --recursive` to list the log files under the workload account's folder, and sends the list through `tee "${EVIDENCE_DIR}/archive-listing.txt"` (which saves it) into `grep -q .` (which is true if there is at least one character, that is, at least one line). If there is output, the `if` branch logs the first five lines with `sed -n '1,5p'` and `break`s out of the loop. Otherwise `log` reports the attempt and `sleep 60` waits.

From `scripts/03-verify-archive.sh` (lines 22 to 23):

```bash
key="$(awk '{print $4}' "${EVIDENCE_DIR}/archive-listing.txt" | sed -n '1p')"
[[ -n "$key" ]] || die "no log file arrived; check aws cloudtrail get-trail-status in the workload account"
```

`awk '{print $4}'` prints the fourth column of each listing line (date, time, size, path), so the path; `sed -n '1p'` keeps only the first line. `[[ -n "$key" ]] || die ...` stops if no log file arrived, and suggests checking the trail's status.

From `scripts/03-verify-archive.sh` (lines 25 to 29):

```bash
log "an administrator of the security account tries to delete a log file: this must be refused (policy deny and Object Lock)"
version="$(aws s3api list-object-versions --bucket "$bucket" --prefix "$key" --query 'Versions[0].VersionId' --output text)"
if aws s3api delete-object --bucket "$bucket" --key "$key" --version-id "$version" 2>&1 | tee "${EVIDENCE_DIR}/delete-by-security-admin.txt"; then
  grep -q AccessDenied "${EVIDENCE_DIR}/delete-by-security-admin.txt" || die "the delete was not refused"
fi
```

The first tamper test: an administrator of the **security** account tries to delete a log file. `aws s3api list-object-versions ... --query 'Versions[0].VersionId' --output text` finds the version id of that file (the bucket is versioned, so a delete must name a version). Then `if aws s3api delete-object ... --version-id "$version" 2>&1 | tee ".../delete-by-security-admin.txt"; then grep -q AccessDenied ... || die ...; fi` attempts the delete, shows and saves the output, and **requires that it was refused**: if the pipeline succeeded, `grep -q AccessDenied` must still find the refusal in the output, or the script stops with "the delete was not refused". The delete is expected to fail, so the `if` is how the script accepts a failing command under `set -e`. Two things refuse it: the bucket's policy and Object Lock ([aws-s3.md](aws-s3.md)).

From `scripts/03-verify-archive.sh` (lines 31 to 35):

```bash
use_account workload
log "an administrator of the workload account tries the same: it has no rights in the security account at all"
if aws s3api delete-object --bucket "$bucket" --key "$key" 2>&1 | tee "${EVIDENCE_DIR}/delete-by-workload-admin.txt"; then
  grep -q AccessDenied "${EVIDENCE_DIR}/delete-by-workload-admin.txt" || die "the delete was not refused"
fi
```

The second tamper test, as an administrator of the **workload** account, which has no rights in the security account at all. `aws s3api delete-object --bucket "$bucket" --key "$key"` is again expected to be refused, and the same `if ... grep -q AccessDenied ... || die` pattern enforces it.

From `scripts/03-verify-archive.sh` (lines 37 to 41):

```bash
log "log file validation with the provider's validator (checks the signatures that verify-archive cannot)"
aws cloudtrail validate-logs --trail-arn "arn:aws:cloudtrail:${REGION}:${WORKLOAD_ACCOUNT_ID}:trail/central-trail" \
  --start-time "$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)" \
  | tee "${EVIDENCE_DIR}/validate-logs.txt"
log "Next: scripts/04-drill-setup.sh"
```

`aws cloudtrail validate-logs` is the provider's own validator: it checks the signatures on the digest files and that the log files match them, which the project's Python code cannot do ([aws-cloudtrail.md](aws-cloudtrail.md)). `--trail-arn` names the trail. `--start-time "$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)"` computes the time one hour ago in a way that works on both systems: `date -v-1H` is the macOS form, and if that fails (`||`), `date -d '1 hour ago'` is the Linux form. The output is shown and saved with `tee`. The last line names the next script.

### `scripts/04-drill-setup.sh`: plant the weakness

From `scripts/04-drill-setup.sh` (lines 1 to 3):

```bash
#!/usr/bin/env bash
# Step 4 of the lesson: plant the weakness (a deliberate, temporary exception) and write down what the credential can do
# BEFORE the drill. The drill user's key is created here, kept only in the AWS CLI profile "drill", and never printed.
```

The comments explain step 4: plant the weakness (a deliberate, temporary exception) and write down what the credential can do **before** the drill. The drill user's key is created here, kept only in the AWS CLI profile `drill`, and never printed.

From `scripts/04-drill-setup.sh` (lines 4 to 7):

```bash
source "$(dirname "$0")/lib.sh"
require terraform
mkdir -p "$EVIDENCE_DIR"
use_account workload
```

`source "$(dirname "$0")/lib.sh"` loads the helper file that sits next to this script. `$0` is the path this script was started with, `dirname` takes its folder, and `source` runs `lib.sh` inside the current shell, so `log`, `die`, `require` and the variables become available (and the `set -euo pipefail` of `lib.sh` applies here too).

`require terraform`, `mkdir -p "$EVIDENCE_DIR"` and `use_account workload` do the usual preparation.

From `scripts/04-drill-setup.sh` (lines 9 to 11):

```bash
sed -i.bak 's/^enable_drill .*/enable_drill        = true/' "${WORKLOAD_ENV}/sandbox.auto.tfvars" && rm -f "${WORKLOAD_ENV}/sandbox.auto.tfvars.bak"
log "TEMPORARY EXCEPTION: creating ${DRILL_USER}, ${DRILL_ROLE} (PowerUserAccess) and a public-capable drill bucket"
"$TF" -chdir="$WORKLOAD_ENV" apply -input=false -auto-approve
```

`sed -i.bak 's/^enable_drill .*/enable_drill        = true/' FILE && rm -f FILE.bak` edits the variables file **in place**: `sed` is a stream editor ([unix-tools.md](unix-tools.md)); `s/old/new/` substitutes; `^enable_drill .*` matches a line that starts with `enable_drill ` and takes the rest of it; `-i.bak` keeps a backup with the suffix `.bak` (written the same way on macOS and Linux), which `rm -f` then removes (`&&`: only if the edit worked). The `log` line announces the temporary exception. `"$TF" ... apply -input=false -auto-approve` then creates the drill user, the over-privileged role and a public-capable bucket ([aws-iam.md](aws-iam.md)).

From `scripts/04-drill-setup.sh` (lines 13 to 20):

```bash
if [[ -z "$(aws iam list-access-keys --user-name "$DRILL_USER" --query 'AccessKeyMetadata[0].AccessKeyId' --output text | grep -v None || true)" ]]; then
  read -r key_id secret < <(aws iam create-access-key --user-name "$DRILL_USER" --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text)
  aws configure set aws_access_key_id "$key_id" --profile drill
  aws configure set aws_secret_access_key "$secret" --profile drill
  aws configure set region "$REGION" --profile drill
  unset secret
  log "the drill key is in the AWS CLI profile 'drill' (id ${key_id}); delete it with scripts/10-teardown.sh"
fi
```

Creating the user's access key, only if it has none. `aws iam list-access-keys --user-name "$DRILL_USER" --query 'AccessKeyMetadata[0].AccessKeyId' --output text | grep -v None || true` prints the user's first key id, or the word `None`; `grep -v None` removes that word, and `|| true` stops `set -e` from ending the script when nothing is left. `[[ -z "$(...)" ]]` is true if the text is **empty** (`-z`), that is, if the user has no key. Then:

- `read -r key_id secret < <(aws iam create-access-key --user-name "$DRILL_USER" --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text)` creates a key and reads its two values into two variables. `<( ... )` is **process substitution**: the shell runs the command and presents its output as a file that `read` can read.
- `aws configure set aws_access_key_id "$key_id" --profile drill` and the next two lines write the key, the secret and the region straight into the AWS CLI profile named `drill`. The secret is never printed and never written to a project file.
- `unset secret` removes the secret from the shell's memory, and `log` reports only the key id.

From `scripts/04-drill-setup.sh` (lines 22 to 29):

```bash
{
  echo "What ${DRILL_ROLE} can do, written down before the drill ($(stamp)):"
  aws iam list-attached-role-policies --role-name "$DRILL_ROLE" --output text
  aws iam list-role-policies --role-name "$DRILL_ROLE" --output text
  echo "What ${DRILL_USER} can do directly:"
  aws iam list-user-policies --user-name "$DRILL_USER" --output text
} | tee "${EVIDENCE_DIR}/drill-capabilities.txt"
log "success test, decided now: the responder identifies every attacker action from the logs and stops the next call. Next: scripts/05-posture-baseline.sh"
```

`{ ...; } | tee FILE` groups several commands so that their combined output goes through one `tee`, which shows it and saves it as the "before" record. It records what the role can do: `aws iam list-attached-role-policies` (managed policies attached to the role), `aws iam list-role-policies` (policies written inside the role) and `aws iam list-user-policies` (policies on the user). `$(stamp)` prints the time. The final `log` states the **success test, decided now**: the responder identifies every attacker action from the logs and stops the next call.

### `scripts/05-posture-baseline.sh`: the findings baseline

From `scripts/05-posture-baseline.sh` (lines 1 to 5):

```bash
#!/usr/bin/env bash
# Step 3 of the lesson: record the posture baseline, then (after you fix what matters) the second reading.
# Usage: 05-posture-baseline.sh before    # right after deploy, writes evidence/posture/before.json
#        05-posture-baseline.sh after     # after fixing, writes after.json and prints the table
# Accept a risk by adding it, with a reason, to docs/posture-acceptances.json.
```

The comments explain the two ways to run it (`before` right after the deploy, `after` once you have fixed what matters) and where accepted risks are recorded.

From `scripts/05-posture-baseline.sh` (lines 6 to 10):

```bash
source "$(dirname "$0")/lib.sh"
phase="${1:-before}"
use_account workload
mkdir -p "${EVIDENCE_DIR}/posture"
log "reading open findings from the posture service (the first full scan takes minutes to hours)"
```

`source "$(dirname "$0")/lib.sh"` loads the helper file that sits next to this script. `$0` is the path this script was started with, `dirname` takes its folder, and `source` runs `lib.sh` inside the current shell, so `log`, `die`, `require` and the variables become available (and the `set -euo pipefail` of `lib.sh` applies here too).

`phase="${1:-before}"` takes the script's first argument (`$1`) or `before` if none was given. `use_account workload` runs the account check. `mkdir -p` creates the folder for the findings. `log` explains that the first full scan takes minutes to hours.

From `scripts/05-posture-baseline.sh` (lines 11 to 13):

```bash
aws securityhub get-findings --region "$REGION" --max-items 1000 \
  --filters '{"ComplianceStatus":[{"Value":"FAILED","Comparison":"EQUALS"}],"WorkflowStatus":[{"Value":"NEW","Comparison":"EQUALS"},{"Value":"NOTIFIED","Comparison":"EQUALS"}],"RecordState":[{"Value":"ACTIVE","Comparison":"EQUALS"}]}' \
  | tee "${EVIDENCE_DIR}/posture/${phase}.json" | python3 -c 'import json, sys; print(len(json.load(sys.stdin)["Findings"]), "open findings")'
```

`aws securityhub get-findings --region "$REGION" --max-items 1000 --filters '{...}'` asks the security-findings service for up to 1000 findings ([aws-security-hub.md](aws-security-hub.md)). The `--filters` argument is a JSON text in single quotes (so the shell passes it unchanged): findings whose compliance status is `FAILED`, whose workflow status is `NEW` or `NOTIFIED`, and whose record state is `ACTIVE` ([json.md](json.md)). The answer goes through `tee ".../posture/${phase}.json"` (saved to `before.json` or `after.json`) and then into `python3 -c '...'`, a one-line Python program that loads the JSON and prints how many findings there are. The trailing `\` continues the command on the next line.

From `scripts/05-posture-baseline.sh` (lines 14 to 16):

```bash
if [[ "$phase" == "after" ]]; then
  "$PY" -m detect_respond posture --findings "${EVIDENCE_DIR}/posture" --accepted "${ROOT}/docs/posture-acceptances.json"
fi
```

Only for `after`: `if [[ "$phase" == "after" ]]; then ... fi` runs the project's `posture` command, which compares the two files and the accepted risks (`--accepted docs/posture-acceptances.json`) and prints the baseline table.

### `scripts/06-honeytoken.sh`: the bait

From `scripts/06-honeytoken.sh` (lines 1 to 3):

```bash
#!/usr/bin/env bash
# Stretch goal: a honeytoken, a credential that should never be used. Creates its key, deploys detection D5 for that key id,
# then uses the key once so you see the alert. The secret half of the key is discarded at once.
```

The comments explain this stretch goal: a **honeytoken** is a credential that should never be used, so any use of it is an intruder. The script creates its key, deploys detection D5 for that key id, and discards the secret half.

From `scripts/06-honeytoken.sh` (lines 4 to 7):

```bash
source "$(dirname "$0")/lib.sh"
require terraform
use_account workload
key_id="$(aws iam create-access-key --user-name honeytoken-svc --query 'AccessKey.AccessKeyId' --output text)"
```

`source "$(dirname "$0")/lib.sh"` loads the helper file that sits next to this script. `$0` is the path this script was started with, `dirname` takes its folder, and `source` runs `lib.sh` inside the current shell, so `log`, `die`, `require` and the variables become available (and the `set -euo pipefail` of `lib.sh` applies here too).

`require terraform` and `use_account workload` do the checks. `key_id="$(aws iam create-access-key --user-name honeytoken-svc --query 'AccessKey.AccessKeyId' --output text)"` creates a key for the bait user and keeps **only the key id** (`--query` picks that one field). The secret half is never read, so it cannot leak.

From `scripts/06-honeytoken.sh` (lines 8 to 12):

```bash
log "honeytoken key id ${key_id}; deploying D5 for it"
printf 'honeytoken_access_key_id = "%s"\n' "$key_id" >> "${WORKLOAD_ENV}/sandbox.auto.tfvars"
"$TF" -chdir="$WORKLOAD_ENV" apply -input=false -auto-approve
log "the alert for any use of this key arrives by email; to see one, sign a call with it (you need the secret, which this script did not keep)."
log "offline, the same detection is replayed by: .venv/bin/python -m detect_respond scan --archive <logs> --honeytoken-key-id ${key_id}"
```

`log` announces the key id. `printf 'honeytoken_access_key_id = "%s"\n' "$key_id" >> FILE` appends one line to the variables file (`>>` appends; `%s` is replaced by the id). Then `apply` runs again, so Terraform deploys detection D5 with that key id filled into its pattern ([aws-eventbridge.md](aws-eventbridge.md)). The two final `log` lines explain that the alert arrives by email on any use of the key, and that offline the same detection is replayed with `scan --archive <logs> --honeytoken-key-id <id>`.

### `scripts/07-drill-attack.sh`: the attacker

From `scripts/07-drill-attack.sh` (lines 1 to 4):

```bash
#!/usr/bin/env bash
# Step 5 of the lesson, the attacker's half. It runs ONLY against the drill resources in your own sandbox: it refuses unless
# the account is the workload account and the targets are the drill user, the drill role and the drill bucket. Write down the
# clock time it prints first: time to detect and time to contain are measured from it.
```

The comments explain: this is the attacker's half of the drill; it runs **only** against the drill resources in your own sandbox; it refuses unless the account is the workload account and the targets are the drill user, the drill role and the drill bucket; and the person must write down the clock time it prints first, because both measured times are counted from it.

From `scripts/07-drill-attack.sh` (lines 5 to 9):

```bash
source "$(dirname "$0")/lib.sh"
mkdir -p "$EVIDENCE_DIR"
use_account workload
bucket="drill-data-${ACCOUNT}"
aws s3api head-bucket --bucket "$bucket" >/dev/null 2>&1 || die "the drill bucket ${bucket} does not exist; run 04-drill-setup.sh"
```

`source "$(dirname "$0")/lib.sh"` loads the helper file that sits next to this script. `$0` is the path this script was started with, `dirname` takes its folder, and `source` runs `lib.sh` inside the current shell, so `log`, `die`, `require` and the variables become available (and the `set -euo pipefail` of `lib.sh` applies here too).

`mkdir -p` and `use_account workload` do the usual preparation. `bucket="drill-data-${ACCOUNT}"` builds the name of the drill bucket. `aws s3api head-bucket --bucket "$bucket" >/dev/null 2>&1 || die "..."` asks whether the bucket exists, hiding all output, and stops with an instruction if not. This is one of the refusals the comment promises: the attack cannot run without the drill setup.

From `scripts/07-drill-attack.sh` (line 11):

```bash
echo "FIRST ATTACKER ACTION AT $(stamp)" | tee "${EVIDENCE_DIR}/first-action.txt"
```

`echo "FIRST ATTACKER ACTION AT $(stamp)" | tee FILE` prints the clock time and saves it. This is the zero point of both measurements.

From `scripts/07-drill-attack.sh` (lines 12 to 14):

```bash
export AWS_PROFILE=drill
read -r ak sk st < <(aws sts assume-role --role-arn "arn:aws:iam::${ACCOUNT}:role/${DRILL_ROLE}" --role-session-name "$SESSION_NAME" \
  --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' --output text)
```

`export AWS_PROFILE=drill` switches the AWS CLI to the profile that holds the drill user's key: from here on the commands act as the leaked credential. `read -r ak sk st < <(aws sts assume-role --role-arn "arn:aws:iam::${ACCOUNT}:role/${DRILL_ROLE}" --role-session-name "$SESSION_NAME" --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' --output text)` uses that key to become the broad role under the session name `intruder` ([aws-sts.md](aws-sts.md)): the three values (key id, secret, session token) are read into three variables, with process substitution `<( ... )` presenting the command's output as a file. They are never printed.

From `scripts/07-drill-attack.sh` (line 15):

```bash
as_role() { AWS_PROFILE='' AWS_ACCESS_KEY_ID="$ak" AWS_SECRET_ACCESS_KEY="$sk" AWS_SESSION_TOKEN="$st" "$@"; }
```

`as_role` runs any command with the **assumed role's** credentials. Putting `NAME=value` words in front of a command sets those variables for that one command only. `AWS_PROFILE=''` empties the profile so the real profile cannot interfere, and the three AWS variables are the standard way the AWS tool finds temporary credentials. `"$@"` is the command to run.

From `scripts/07-drill-attack.sh` (lines 17 to 20):

```bash
log "look around";                  as_role aws s3 ls >/dev/null
log "D1: a new key for ${DRILL_USER}"; as_role aws iam create-access-key --user-name "$DRILL_USER" --query 'AccessKey.AccessKeyId' --output text >/dev/null
log "D2: the drill bucket made public"; as_role aws s3api put-bucket-acl --bucket "$bucket" --acl public-read
log "D4: a call in a Region the account does not use"; as_role aws ec2 describe-instances --region ap-southeast-2 >/dev/null
```

The attacker's four steps, each logged first. `;` separates the `log` from the command on one line.

- **Look around**: `as_role aws s3 ls >/dev/null` lists buckets (and discards the output). A read-only call; most real intrusions start this way.
- **D1**: `as_role aws iam create-access-key --user-name "$DRILL_USER" --query 'AccessKey.AccessKeyId' --output text >/dev/null` mints a new long-lived key, which is a persistence step; detection D1 watches for it.
- **D2**: `as_role aws s3api put-bucket-acl --bucket "$bucket" --acl public-read` makes the drill bucket publicly readable; detection D2 watches for it.
- **D4**: `as_role aws ec2 describe-instances --region ap-southeast-2 >/dev/null` makes a call in a Region the account does not use; detection D4 watches for it.

From `scripts/07-drill-attack.sh` (lines 21 to 24):

```bash
echo "LAST ATTACKER ACTION AT $(stamp)" | tee -a "${EVIDENCE_DIR}/first-action.txt"
log "the credentials stay in this shell only. Now be the responder: read your email, then scripts/08-contain.sh"
printf '%s\n' "$ak" > "${EVIDENCE_DIR}/.session-key-id"
unset sk st
```

The last attacker action is stamped too (`tee -a` **appends** to the same file). The `log` line says the credentials stay in this shell only and tells the person to become the responder. `printf '%s\n' "$ak" > ".../.session-key-id"` saves only the session's key id (for the person's notes), and `unset sk st` removes the secret and the token from the shell's memory.

### `scripts/08-contain.sh`: the responder

From `scripts/08-contain.sh` (lines 1 to 4):

```bash
#!/usr/bin/env bash
# Step 5, the responder's half: contain from the evidence. Without --apply it only prints what it would do.
# It denies every session of the role issued before now AND deactivates the user's keys; revoking only the key leaves the
# role's sessions alive until they expire.
```

The comments explain: contain from the evidence; without `--apply` the script only prints what it would do; it denies every session of the role issued before now **and** deactivates the user's keys, because revoking only the key leaves the role's sessions alive until they expire.

From `scripts/08-contain.sh` (lines 5 to 8):

```bash
source "$(dirname "$0")/lib.sh"
mkdir -p "$EVIDENCE_DIR"
use_account workload
mode=("$@")  # empty without --apply; the "+" forms below keep Bash 3.2 (macOS) from failing on an empty array under set -u
```

`source "$(dirname "$0")/lib.sh"` loads the helper file that sits next to this script. `$0` is the path this script was started with, `dirname` takes its folder, and `source` runs `lib.sh` inside the current shell, so `log`, `die`, `require` and the variables become available (and the `set -euo pipefail` of `lib.sh` applies here too).

`mkdir -p` and `use_account workload` do the usual preparation. `mode=("$@")` stores all of the script's arguments in an **array** named `mode`: empty for a dry run, or holding `--apply`. Everything after `#` on that line is a comment, written for the next reader: the array is empty in the default case, and the two lines below use the `+` form so that case also works on the old Bash 3.2 of macOS.

From `scripts/08-contain.sh` (line 9):

```bash
"$PY" -m detect_respond contain --role "$DRILL_ROLE" --user "$DRILL_USER" ${mode[@]+"${mode[@]}"} | tee -a "${EVIDENCE_DIR}/containment.txt"
```

`"$PY" -m detect_respond contain --role "$DRILL_ROLE" --user "$DRILL_USER" ${mode[@]+"${mode[@]}"}` runs the project's `contain` command, passing along whatever was given ([aws-iam.md](aws-iam.md)). `${mode[@]+"${mode[@]}"}` expands the array into separate arguments, keeping each as one word. The pattern `${name+word}` means: if the variable `name` is set, use `word`; if it is not set, use nothing at all. For an array, "set" means "has at least one element", so `${mode[@]+"${mode[@]}"}` expands to the quoted words when the array has elements and to nothing when it is empty, and it never counts as an unbound variable. This is the form that works on every Bash, including the 3.2 that macOS ships, where a plain `"${mode[@]}"` of an empty array under `set -u` stops with `unbound variable`. `| tee -a ".../containment.txt"` shows the output and appends it to a record.

From `scripts/08-contain.sh` (lines 10 to 13):

```bash
if [[ "${mode[*]+${mode[*]}}" == *--apply* ]]; then
  echo "CONTAINED AT $(stamp)" | tee -a "${EVIDENCE_DIR}/containment.txt"
  log "to prove it, run the attacker's next call (the profile and session from 07-drill-attack.sh) and see AccessDenied"
fi
```

`[[ "${mode[*]+${mode[*]}}" == *--apply* ]]` joins the array into one string (`[*]` joins, `[@]` keeps separate words; the `+` form gives an empty string for an empty array instead of an unbound-variable error on Bash 3.2) and tests whether it contains `--apply` anywhere (`*` matches any text). Only then does the script stamp the moment of containment (`echo "CONTAINED AT $(stamp)" | tee -a ...`) and tell the person how to prove it: run the attacker's next call and see `AccessDenied`. In a dry run nothing is stamped, because nothing changed.

### `scripts/09-collect-and-measure.sh`: the timeline and the numbers

From `scripts/09-collect-and-measure.sh` (lines 1 to 5):

```bash
#!/usr/bin/env bash
# Steps 5 and 6: copy the archive out of the security account, check it was not altered, rebuild the timeline from the logs
# alone, measure time to detect and time to contain, and write the blameless review. Put the times your alerts reached you in
# evidence/alerts.json ({"alerts": [{"eventId": "...", "receivedAt": "2026-10-22T11:03:42Z"}]}) to measure real latency; without
# it the event time is used, which is the lower bound.
```

The comments explain steps 5 and 6: copy the archive out of the security account, check it was not altered, rebuild the timeline from the logs alone, measure the two times and write the blameless review; and how to give the times your alerts really reached you in `evidence/alerts.json` (without it the event time is used, which is the lower bound).

From `scripts/09-collect-and-measure.sh` (lines 6 to 10):

```bash
source "$(dirname "$0")/lib.sh"
mkdir -p "${EVIDENCE_DIR}/archive"
use_account security
log "syncing the archive (events can lag by 5 to 15 minutes)"
aws s3 sync "s3://$(archive_bucket)/AWSLogs/" "${EVIDENCE_DIR}/archive/AWSLogs/" --only-show-errors
```

`source "$(dirname "$0")/lib.sh"` loads the helper file that sits next to this script. `$0` is the path this script was started with, `dirname` takes its folder, and `source` runs `lib.sh` inside the current shell, so `log`, `die`, `require` and the variables become available (and the `set -euo pipefail` of `lib.sh` applies here too).

`mkdir -p` makes the folder for the archive copy; `use_account security` works in the security account; `log` explains that events can lag by 5 to 15 minutes; and `aws s3 sync "s3://$(archive_bucket)/AWSLogs/" "${EVIDENCE_DIR}/archive/AWSLogs/" --only-show-errors` copies the new log and digest files down into a local folder (`sync` copies only what is new; `--only-show-errors` hides progress lines).

From `scripts/09-collect-and-measure.sh` (lines 11 to 13):

```bash
"$PY" -m detect_respond verify-archive --archive "${EVIDENCE_DIR}/archive"
alerts=()
[[ -f "${EVIDENCE_DIR}/alerts.json" ]] && alerts=(--alerts "${EVIDENCE_DIR}/alerts.json")
```

`verify-archive` checks every log file against its digest, so the later analysis rests on files that were not altered. `alerts=()` creates an **empty array**. `[[ -f "${EVIDENCE_DIR}/alerts.json" ]] && alerts=(--alerts "${EVIDENCE_DIR}/alerts.json")` fills it with two words only if that file exists (`-f`: a regular file exists). An array is used so that the two words stay two separate arguments later.

From `scripts/09-collect-and-measure.sh` (lines 14 to 16):

```bash
"$PY" -m detect_respond scan --archive "${EVIDENCE_DIR}/archive" --expect D1,D2,D4 | tail -n 1
"$PY" -m detect_respond drill --archive "${EVIDENCE_DIR}/archive" ${alerts[@]+"${alerts[@]}"} | tee "${EVIDENCE_DIR}/timeline.txt"
"$PY" -m detect_respond review --archive "${EVIDENCE_DIR}/archive" ${alerts[@]+"${alerts[@]}"} --output "${EVIDENCE_DIR}/REVIEW.md"
```

Three commands, all run on the **local copy**: `scan --archive ... --expect D1,D2,D4 | tail -n 1` runs every detection over the archive and fails if D1, D2 or D4 does not fire (`tail -n 1` keeps the last line, the summary); `drill --archive ... ${alerts[@]+"${alerts[@]}"} | tee ".../timeline.txt"` rebuilds the attacker's timeline and measures time to detect and time to contain, saving the output; `review --archive ... ${alerts[@]+"${alerts[@]}"} --output ".../REVIEW.md"` writes the blameless review. `${alerts[@]+"${alerts[@]}"}` expands the array into its words, or into nothing when it is empty, on every Bash version. The pattern `${name+word}` means: if the variable `name` is set, use `word`; if it is not set, use nothing at all. For an array, "set" means "has at least one element", so `${alerts[@]+"${alerts[@]}"}` expands to the quoted words when the array has elements and to nothing when it is empty, and it never counts as an unbound variable. This is the form that works on every Bash, including the 3.2 that macOS ships, where a plain `"${alerts[@]}"` of an empty array under `set -u` stops with `unbound variable`.

From `scripts/09-collect-and-measure.sh` (line 17):

```bash
log "the review is ${EVIDENCE_DIR}/REVIEW.md. Edit its wording if you like, but keep an event id on every claim."
```

`log` says where the review is, and that its wording may be edited as long as every claim keeps an event id.

### `scripts/10-teardown.sh`: remove the exception, then the rest

From `scripts/10-teardown.sh` (lines 1 to 4):

```bash
#!/usr/bin/env bash
# Step 6: remove the temporary exception and delete the workload account's resources, then write the time down. The archive in
# the security account cannot be deleted until its Object Lock retention (one day) and the lifecycle expiry (two days) have
# passed: run `10-teardown.sh archive` after that. Run it even if a step failed.
```

The comments explain: remove the temporary exception, delete the workload account's resources and write the time down; the archive in the security account cannot be deleted until its Object Lock retention (one day) and its lifecycle expiry (two days) have passed, after which `10-teardown.sh archive` removes it; run the script even if a step failed.

From `scripts/10-teardown.sh` (lines 5 to 13):

```bash
source "$(dirname "$0")/lib.sh"
require terraform
if [[ "${1:-}" == "archive" ]]; then
  use_account security
  "$TF" -chdir="$SECURITY_ENV" destroy -input=false -auto-approve
  rm -f "${SECURITY_ENV}/sandbox.auto.tfvars"
  log "archive destroyed"
  exit 0
fi
```

`source "$(dirname "$0")/lib.sh"` loads the helper file that sits next to this script. `$0` is the path this script was started with, `dirname` takes its folder, and `source` runs `lib.sh` inside the current shell, so `log`, `die`, `require` and the variables become available (and the `set -euo pipefail` of `lib.sh` applies here too).

`require terraform` checks the tool. `if [[ "${1:-}" == "archive" ]]; then ... fi` handles the second mode: with the argument `archive`, the script switches to the security account (`use_account security`), runs `destroy` on the security environment, deletes the variables file and logs it, and `exit 0` ends the script there. Otherwise the code after the `fi` runs.

From `scripts/10-teardown.sh` (lines 15 to 22):

```bash
use_account workload
log "removing the drill key and profile first"
for key in $(aws iam list-access-keys --user-name "$DRILL_USER" --query 'AccessKeyMetadata[].AccessKeyId' --output text 2>/dev/null); do
  aws iam delete-access-key --user-name "$DRILL_USER" --access-key-id "$key"
done
for key in $(aws iam list-access-keys --user-name honeytoken-svc --query 'AccessKeyMetadata[].AccessKeyId' --output text 2>/dev/null); do
  aws iam delete-access-key --user-name honeytoken-svc --access-key-id "$key"
done
```

The normal mode. `use_account workload` points at the workload account and `log` announces the first task: remove the drill key and the profile first. Two loops delete keys: `for key in $(aws iam list-access-keys --user-name "$DRILL_USER" --query 'AccessKeyMetadata[].AccessKeyId' --output text 2>/dev/null); do aws iam delete-access-key ...; done` lists the user's key ids and deletes each; `2>/dev/null` hides the error if the user no longer exists, in which case the loop has nothing to do. The second loop does the same for the honeytoken user. (Teardown, unlike containment, wants the credential **gone**, so it deletes and does not merely deactivate.)

From `scripts/10-teardown.sh` (line 23):

```bash
aws configure set aws_access_key_id "" --profile drill && aws configure set aws_secret_access_key "" --profile drill || true
```

Empties the `drill` profile: `aws configure set aws_access_key_id "" --profile drill && aws configure set aws_secret_access_key "" --profile drill || true` sets both stored values to nothing; `|| true` keeps `set -e` from ending the script if the profile does not exist.

From `scripts/10-teardown.sh` (lines 25 to 27):

```bash
"$TF" -chdir="$WORKLOAD_ENV" destroy -input=false -auto-approve
rm -f "${WORKLOAD_ENV}/sandbox.auto.tfvars"
echo "EXCEPTION REMOVED AT $(stamp)" | tee -a "${EVIDENCE_DIR}/containment.txt"
```

`destroy -input=false -auto-approve` deletes every resource of the workload environment without asking. `rm -f` removes the variables file. `echo "EXCEPTION REMOVED AT $(stamp)" | tee -a ...` stamps the time the weakness was removed and appends it to the same record file as the containment time.

From `scripts/10-teardown.sh` (lines 28 to 32):

```bash
log "what still carries the project tag:"
aws resourcegroupstaggingapi get-resources --region "$REGION" --tag-filters Key=project,Values=detect-and-respond \
  --query 'ResourceTagMappingList[].ResourceARN' --output text || true
log "the security account's archive remains until its retention ends; then run: scripts/10-teardown.sh archive"
log "check the bill tomorrow: Config, Security Hub and keys cost money while they exist."
```

`log` announces a check of what is left. `aws resourcegroupstaggingapi get-resources --region "$REGION" --tag-filters Key=project,Values=detect-and-respond --query 'ResourceTagMappingList[].ResourceARN' --output text || true` lists every resource that still carries the project tag ([terraform-aws-provider.md](terraform-aws-provider.md)); `|| true` keeps going if the call fails. The last three `log` lines explain that the archive stays until its retention ends and then needs `scripts/10-teardown.sh archive`, and that the bill should be checked the next day because Config, Security Hub and keys cost money while they exist.

## Try it yourself

```bash
for f in scripts/*.sh; do bash -n "$f" && echo "ok $f"; done
```

`-n` checks syntax without running. Expect eleven `ok scripts/...` lines.

```bash
SECURITY_PROFILE= bash -c 'source scripts/lib.sh; use_account security'; echo "exit $?"
```

Expect `error: set SECURITY_PROFILE to the AWS CLI profile of the security account` and `exit 1`. The guard refuses before any call.

```bash
bash -c 'source scripts/lib.sh; use_account nope'; echo "exit $?"
```

Expect `error: unknown account nope` and `exit 1`: the `*)` branch of the `case`.

```bash
bash -c 'v=SECURITY_PROFILE; SECURITY_PROFILE=prof; echo "${!v}"'
```

Expect `prof`: indirect expansion.

```bash
bash -c 'mode=(); if [[ "${mode[*]}" == *--apply* ]]; then echo apply; else echo dry; fi'
```

Expect `dry`: an empty argument list means a dry run.

## Mistakes people make

- Unquoted variables (`rm -rf $dir`). A value with a space or `*` changes what runs. ShellCheck flags it.
- Missing `set -euo pipefail`, so a failed step is ignored and the script goes on.
- Expanding an **empty array** under `set -u` on Bash 3.2. A plain `"${mode[@]}"` (or `"${mode[*]}"`) of an empty array stops with `unbound variable` on the Bash 3.2 that macOS ships as `/bin/bash`; Bash 4.4 and newer accept it. This repository hit it: the default case of `08-contain.sh` (a dry run, no arguments) and of `09-collect-and-measure.sh` (no `alerts.json`) has an empty array. Both scripts now use the portable form `${mode[@]+"${mode[@]}"}` (and `"${mode[*]+${mode[*]}}"` for the joined string), and were run under `/bin/bash` 3.2.57 and under Bash 5.3 with a stand-in `aws` and Python to confirm it. Write the portable form whenever an array can be empty.
- Putting secrets in command-line arguments, where `ps` shows them. The drill key goes straight into a CLI profile and is never printed.
- Forgetting that a quoted here-document marker (`<<'PY'`) stops variable substitution and an unquoted one (`<<TFVARS`) allows it.

## Check yourself

1. What does `set -euo pipefail` do? *Stops on errors, errors on unset variables, and fails a pipeline if any part fails.*
2. What does `${!profile_var}` mean? *The value of the variable whose name is stored in `profile_var`.*
3. Why does `use_account` exist? *No script touches AWS until the profile is shown to belong to the named account and not to the root user.*
4. Why is `mode` an array and not a string? *Each argument stays one word, so a value with spaces is passed unchanged.*
5. Why does `03-verify-archive.sh` accept a failing delete? *The delete is supposed to be refused; the script requires `AccessDenied` in the output.*

## Further reading

- GNU Bash reference manual: <https://www.gnu.org/software/bash/manual/bash.html> (Bash 5.3)
