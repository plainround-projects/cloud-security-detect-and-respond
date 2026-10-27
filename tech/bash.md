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

### The library file

From `scripts/lib.sh`:

```bash
#!/usr/bin/env bash
# shellcheck disable=SC2034
set -euo pipefail
```

- `#!/usr/bin/env bash` finds `bash` on your `PATH`.
- The `# shellcheck` line is a directive for the checker ([shellcheck.md](shellcheck.md)): variables such as `DRILL_ROLE` look unused inside this file, because they are used by the scripts that source it.
- `set -euo pipefail` is the safety switch: `-e` stops at the first command that fails; `-u` treats an unset variable as an error; `-o pipefail` makes a pipeline fail if *any* command in it fails, not only the last. Because the numbered scripts `source` this file, the switch applies to them too.

From `scripts/lib.sh`:

```bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGION="${AWS_REGION:-eu-west-1}"
DRILL_ROLE="drill-broad-role"
SESSION_NAME="intruder"
```

- `$(...)` runs a command and substitutes its output. `${BASH_SOURCE[0]}` is the path of the file being run; `dirname` removes the file name; `/..` goes up one folder; `cd ... && pwd` prints the absolute path. The result is the repository root, wherever you started the script.
- `${AWS_REGION:-eu-west-1}` means "the value of `AWS_REGION`, or `eu-west-1` if it is unset or empty".
- The names used by the drill are set once, so no script spells them twice.

From `scripts/lib.sh`:

```bash
log() { printf '%s %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }
```

A **function** is a named group of commands. `$*` is all the arguments joined. `log` prints a UTC time and a message. `die` prints to **standard error** (`>&2`) and ends the script with exit code 1.

From `scripts/lib.sh`:

```bash
require() {
  for tool in "$@"; do command -v "$tool" >/dev/null 2>&1 || die "$tool is required"; done
}
```

`"$@"` is every argument as a separate quoted word. `command -v tool` succeeds if the tool exists. `>/dev/null 2>&1` throws away all its output. `a || b` runs `b` only if `a` failed.

### Two accounts, one guard

From `scripts/lib.sh`:

```bash
  case "$which" in
    security) profile_var=SECURITY_PROFILE; expected_var=SECURITY_ACCOUNT_ID ;;
    workload) profile_var=WORKLOAD_PROFILE; expected_var=WORKLOAD_ACCOUNT_ID ;;
    *) die "unknown account $which" ;;
  esac
```

A `case` picks a branch by matching a word against patterns. Each branch ends with `;;`. `*)` matches anything else. Here the function remembers the *names* of two variables rather than their values.

From `scripts/lib.sh`:

```bash
  [[ -n "${!profile_var:-}" ]] || die "set ${profile_var} to the AWS CLI profile of the ${which} account"
  export AWS_PROFILE="${!profile_var}"
```

`${!name}` is **indirect expansion**: if `profile_var` holds the text `SECURITY_PROFILE`, then `${!profile_var}` is the value of the variable `SECURITY_PROFILE`. `[[ -n ... ]]` is a test: true when the string is not empty. `:-` inside it gives an empty string if the variable is unset, which keeps `set -u` happy. `export` hands the variable to programs started later: from now on the AWS CLI uses that profile.

From `scripts/lib.sh`:

```bash
  ACCOUNT="${identity%%$'\t'*}"
  arn="${identity##*$'\t'}"
```

`aws sts get-caller-identity --query '[Account,Arn]' --output text` prints the account and ARN separated by a tab ([aws-sts.md](aws-sts.md)). `${identity%%$'\t'*}` removes the longest match of "tab and everything after" from the end, leaving the account id. `${identity##*$'\t'}` removes everything up to the last tab, leaving the ARN. `$'\t'` is how Bash writes a tab.

From `scripts/lib.sh`:

```bash
  [[ "$arn" != *":root" ]] || die "do not run this as the account root user; use an administrator role or user"
```

`!= *":root"` is true unless the text ends with `:root`. This function is the main safety feature: no script touches AWS until the profile is shown to belong to the account you named, and not to the root user.

### Writing the variables, with a here-document

From `scripts/01-deploy-security.sh`:

```bash
: "${WORKLOAD_ACCOUNT_ID:?set WORKLOAD_ACCOUNT_ID}"
```

`:` is a command that does nothing; its argument is expanded first. `${NAME:?message}` stops the script with the message if `NAME` is unset or empty. It is a one-line "required variable" check.

From `scripts/01-deploy-security.sh`:

```bash
cat > "${SECURITY_ENV}/sandbox.auto.tfvars" <<TFVARS
security_account_id = "${ACCOUNT}"
workload_account_id = "${WORKLOAD_ACCOUNT_ID}"
retention_days      = 1
expire_days         = 2
TFVARS
```

A **here-document**: everything up to the line `TFVARS` becomes the input of `cat`, which writes it to the file. Because `TFVARS` is not quoted, Bash substitutes `${ACCOUNT}` inside it. The file is ignored by git ([git.md](git.md)).

### Polling, and an edit in place

From `scripts/03-verify-archive.sh`:

```bash
for attempt in $(seq 1 20); do
```

`seq 1 20` prints 1 to 20; the loop runs 20 times with `attempt` set to each. The body lists the archive, `break`s when it finds a file, and otherwise sleeps 60 seconds ([unix-tools.md](unix-tools.md)). This handles CloudTrail's delay ([aws-cloudtrail.md](aws-cloudtrail.md)).

From `scripts/03-verify-archive.sh`:

```bash
if aws s3api delete-object --bucket "$bucket" --key "$key" --version-id "$version" 2>&1 | tee "${EVIDENCE_DIR}/delete-by-security-admin.txt"; then
  grep -q AccessDenied "${EVIDENCE_DIR}/delete-by-security-admin.txt" || die "the delete was not refused"
fi
```

The delete is *expected* to fail. Under `pipefail` a failing `aws` makes the whole pipeline fail, and the `if` swallows that failure. If the pipeline somehow succeeded, the `grep` must still find `AccessDenied` in the output, or the script dies: a delete that went through is the one outcome this test must not accept.

From `scripts/04-drill-setup.sh`:

```bash
sed -i.bak 's/^enable_drill .*/enable_drill        = true/' "${WORKLOAD_ENV}/sandbox.auto.tfvars" && rm -f "${WORKLOAD_ENV}/sandbox.auto.tfvars.bak"
```

`sed -i.bak` edits the file in place and keeps a copy with the suffix `.bak`. Writing the suffix without a space works the same on macOS and Linux (plain `-i` does not). `s/old/new/` substitutes; `^` anchors to the line start. `&&` removes the backup only if the edit worked.

### The attacker's half

From `scripts/07-drill-attack.sh`:

```bash
as_role() { AWS_PROFILE='' AWS_ACCESS_KEY_ID="$ak" AWS_SECRET_ACCESS_KEY="$sk" AWS_SESSION_TOKEN="$st" "$@"; }
```

Putting `NAME=value` before a command sets that variable for that command only. `as_role aws s3 ls` runs `aws s3 ls` with the assumed role's temporary credentials and an *empty* profile, so the real profile cannot interfere. The credentials come from the line `read -r ak sk st < <(aws sts assume-role ...)`: `<( ... )` is **process substitution** (the command's output presented as a file), and `read -r ak sk st` splits one line into three variables. The secrets are never printed.

From `scripts/07-drill-attack.sh`:

```bash
echo "FIRST ATTACKER ACTION AT $(stamp)" | tee "${EVIDENCE_DIR}/first-action.txt"
```

The script prints the clock time before the first call, because both measured times start from it. `tee` shows the line and saves it.

### The responder's half

From `scripts/08-contain.sh`:

```bash
mode=("$@")
```

An **array**: `mode` holds all the script's arguments as separate items. With `make respond` it is empty (a dry run); with `make respond APPLY=--apply` it holds `--apply`.

From `scripts/08-contain.sh`:

```bash
if [[ "${mode[*]}" == *--apply* ]]; then
```

`"${mode[*]}"` joins the items into one string, and `*--apply*` matches if the string contains that word anywhere. Only then does the script write the `CONTAINED AT` stamp.

From `scripts/09-collect-and-measure.sh`:

```bash
[[ -f "${EVIDENCE_DIR}/alerts.json" ]] && alerts=(--alerts "${EVIDENCE_DIR}/alerts.json")
```

`[[ -f path ]]` tests that a file exists. When it does, the array gets the two words `--alerts` and the path, which later become two separate arguments of the command. This is why an array is used and not a string: a path with a space would stay one word.

### Cleaning up

From `scripts/10-teardown.sh`:

```bash
for key in $(aws iam list-access-keys --user-name "$DRILL_USER" --query 'AccessKeyMetadata[].AccessKeyId' --output text 2>/dev/null); do
```

The loop runs once for each key id the command prints. `2>/dev/null` hides the error if the user no longer exists, and the loop then has nothing to do. Deleting the key here is correct: teardown, unlike containment, wants the credential gone.

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
- Expanding an **empty array** under `set -u` on Bash 3.2. `"${mode[@]}"` in `08-contain.sh` and `"${alerts[@]}"` in `09-collect-and-measure.sh` fail there with `unbound variable` when the array is empty, which is the default case in both (the dry run, and no `alerts.json`). Bash 4.4 and newer accept it. On macOS with the stock `/bin/bash`, run the scripts with a newer Bash (`brew install bash`) until they are changed to the portable form `${mode[@]+"${mode[@]}"}`.
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
