# Small Unix tools in the scripts: date, seq, sleep, grep, sed, awk, tee, tail, cut, sort

## What it is

These are tiny command-line programs that come with macOS and Linux. Each does one job; the shell ([bash.md](bash.md)) connects them. None needs installing.

| Program | Job |
| --- | --- |
| `date` | prints or formats the time |
| `seq` | prints a range of numbers |
| `sleep` | pauses |
| `grep` | finds lines that match a pattern |
| `sed` | edits a stream of text |
| `awk` | picks columns out of lines |
| `tee` | copies its input to the screen and to a file |
| `tail`, `head` | keep the last or first lines |
| `cut` | keeps a range of characters of each line |
| `sort` | puts lines in order |

## Why this repository uses it

The runbook scripts and the Makefile need small jobs without writing a program: stamp the clock time of the attacker's first action, wait for the log file to arrive, pick the path out of a listing, save evidence while showing it, and shorten long output.

## Where it appears

| Path | Use |
| --- | --- |
| `scripts/lib.sh` | `date -u` for log lines and for `stamp` |
| `scripts/03-verify-archive.sh` | `seq`, `sleep`, `tee`, `grep -q`, `awk` and `sed -n` to take the first file path |
| `scripts/04-drill-setup.sh` | `sed -i.bak` to switch a setting in the variables file |
| `scripts/07-drill-attack.sh`, `08-contain.sh` | `tee` to save the time stamps |
| `scripts/09-collect-and-measure.sh` | `tail -n 1` to keep the scan's summary line |
| `Makefile` | `grep`, `sed`, `sort` in `make help`; `tail`, `cut` in `demo-drill` |

## How it works underneath

Each program reads from **standard input**, writes to **standard output** and writes errors to **standard error**. The pipe `|` connects one program's output to the next one's input. A program tells the shell whether it worked by its **exit code** (0 is success). `grep` uses exit code 1 for "no match", so `grep -q` can serve as a yes/no question.

## Walkthrough of this repository's use

From `scripts/lib.sh`:

```bash
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
```

`date -u +FORMAT` prints the current time in UTC (`-u`). `%Y-%m-%dT%H:%M:%SZ` gives year-month-day, a `T`, hours:minutes:seconds and a literal `Z` for "UTC": the same form the audit log uses ([python.md](python.md) parses it). The clock time of the attacker's first action and of containment are printed this way, and the review measures from them.

From `scripts/03-verify-archive.sh`:

```bash
  log "nothing yet (attempt ${attempt} of 20)"; sleep 60
```

`sleep 60` pauses for 60 seconds. Together with `seq 1 20` (see [bash.md](bash.md)) it bounds the wait for the log file at 20 minutes.

From `scripts/03-verify-archive.sh`:

```bash
key="$(awk '{print $4}' "${EVIDENCE_DIR}/archive-listing.txt" | sed -n '1p')"
```

`aws s3 ls` prints one line per file: date, time, size and path. `awk '{print $4}'` prints the fourth whitespace-separated column, the path. `sed -n '1p'` prints only line 1 (`-n` turns off the default printing; `1p` prints line 1). The result is the first log file, whose delete the script then tries.

From `scripts/04-drill-setup.sh`:

```bash
sed -i.bak 's/^enable_drill .*/enable_drill        = true/' "${WORKLOAD_ENV}/sandbox.auto.tfvars" && rm -f "${WORKLOAD_ENV}/sandbox.auto.tfvars.bak"
```

`s/old/new/` substitutes text. `^enable_drill .*` matches a line that starts with `enable_drill ` and takes the rest of the line; the replacement is the same setting set to `true`. `-i.bak` edits in place and keeps a backup, written the same way on macOS and Linux.

From `scripts/09-collect-and-measure.sh`:

```bash
"$PY" -m detect_respond scan --archive "${EVIDENCE_DIR}/archive" --expect D1,D2,D4 | tail -n 1
```

`tail -n 1` keeps only the last line of the output: the summary, such as `6 alerts from detections: D1, D2, D4`, without the alert text. The scan's exit code is lost in the pipe unless `pipefail` is on, which it is in the scripts.

From `Makefile`:

```make
	@$(DR) contain --access-key-id AKIADRILLEXAMPLE0001 | cut -c1-160
```

`cut -c1-160` keeps the first 160 characters of each line, so the long policy JSON in the dry run does not flood the screen.

From `Makefile`:

```make
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | sort
```

`grep -E` uses extended patterns and keeps the lines that define a documented target; `sed -E 's/:.*## /\t/'` replaces everything from the colon to `## ` with a tab; `sort` orders the lines. This is `make help` ([make.md](make.md)).

### Every program and flag, one by one

This is the complete list of the Unix command-line programs that the scripts, the `Makefile`, the workflow file and the server template of this repository run, with every flag they are given. (`aws` is in [aws-cli.md](aws-cli.md), `terraform` in [terraform.md](terraform.md), `python3` in [python.md](python.md), `make` in [make.md](make.md), and the shell's own words such as `if`, `for`, `source` and `echo` in [bash.md](bash.md).) A **flag** is a word that starts with `-` and changes how the program behaves. A line may appear under two tools when it uses a pipe, which sends the output of one program to the next.

#### `sed`

`sed`: **stream editor**: reads text line by line and prints it after applying small edit commands. Used for: take a line out of a listing, or edit a settings file.

Flags used:

- `-E`: use extended regular expressions (parentheses and `|` without backslashes).
- `-n`: print nothing unless a command asks to (`p`).
- `-i.bak`: edit the file in place and keep the original with the suffix `.bak`; this spelling works on both macOS and Linux sed.

Every use:

- `Makefile` line 19: `@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | sort`
- `scripts/03-verify-archive.sh` line 18: `log "the archive holds log files:"; sed -n '1,5p' "${EVIDENCE_DIR}/archive-listing.txt"; break`
- `scripts/03-verify-archive.sh` line 22: `key="$(awk '{print $4}' "${EVIDENCE_DIR}/archive-listing.txt" | sed -n '1p')"`
- `scripts/04-drill-setup.sh` line 9: `sed -i.bak 's/^enable_drill .*/enable_drill        = true/' "${WORKLOAD_ENV}/sandbox.auto.tfvars" && rm -f "${WORKLOAD_ENV}/sandbox.auto.tfvars.bak"`

#### `grep`

`grep`: prints the lines that match a pattern (or, with `-q`, only answers yes or no through its exit code). Used for: filter output and test whether a text appears.

Flags used:

- `-E`: extended regular expressions.
- `-q`: quiet: print nothing, only set the exit code (0 when a match was found).
- `-v`: invert: keep the lines that do **not** match.

Every use:

- `Makefile` line 67: `$(OFFLINE) $(TF) -chdir=$$dir plan -var-file=plan-only.tfvars -out=$(CURDIR)/$(BUILD)/$$env.tfplan -input=false -lock=false -no-color | grep -E "^Plan:|Error" && \`
- `scripts/03-verify-archive.sh` line 17: `if aws s3 ls "s3://${bucket}/AWSLogs/${WORKLOAD_ACCOUNT_ID}/CloudTrail/" --recursive | tee "${EVIDENCE_DIR}/archive-listing.txt" | grep -q .; then`
- `scripts/03-verify-archive.sh` line 28: `grep -q AccessDenied "${EVIDENCE_DIR}/delete-by-security-admin.txt" || die "the delete was not refused"`
- `scripts/03-verify-archive.sh` line 34: `grep -q AccessDenied "${EVIDENCE_DIR}/delete-by-workload-admin.txt" || die "the delete was not refused"`
- `scripts/04-drill-setup.sh` line 13: `if [[ -z "$(aws iam list-access-keys --user-name "$DRILL_USER" --query 'AccessKeyMetadata[0].AccessKeyId' --output text | grep -v None || true)" ]]; then`

#### `awk`

`awk`: a tiny language for splitting each line into columns and printing some of them. Used for: pick the fourth column of a listing.

Every use:

- `scripts/03-verify-archive.sh` line 22: `key="$(awk '{print $4}' "${EVIDENCE_DIR}/archive-listing.txt" | sed -n '1p')"`

#### `cut`

`cut`: keeps selected columns or character positions of every line. Used for: shorten long lines.

Flags used:

- `-c1-160`: keep characters 1 to 160 of each line.

Every use:

- `Makefile` line 92: `@$(DR) contain --access-key-id AKIADRILLEXAMPLE0001 | cut -c1-160`

#### `sort`

`sort`: puts lines in order. Used for: order the help lines.

Every use:

- `Makefile` line 19: `@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | sort`

#### `tail`

`tail`: prints the end of its input. Used for: keep a summary line.

Flags used:

- `-n`: how many lines to print from the end.

Every use:

- `Makefile` line 84: `@$(DR) scan --archive $(REHEARSAL) --expect D1,D2,D4 | tail -n 1`
- `scripts/09-collect-and-measure.sh` line 14: `"$PY" -m detect_respond scan --archive "${EVIDENCE_DIR}/archive" --expect D1,D2,D4 | tail -n 1`

#### `tee`

`tee`: copies what it reads to standard output **and** to a file, so you can watch and keep. Used for: show and keep evidence.

Flags used:

- `-a`: append to the file instead of replacing it.

Every use:

- `scripts/03-verify-archive.sh` line 17: `if aws s3 ls "s3://${bucket}/AWSLogs/${WORKLOAD_ACCOUNT_ID}/CloudTrail/" --recursive | tee "${EVIDENCE_DIR}/archive-listing.txt" | grep -q .; then`
- `scripts/03-verify-archive.sh` line 27: `if aws s3api delete-object --bucket "$bucket" --key "$key" --version-id "$version" 2>&1 | tee "${EVIDENCE_DIR}/delete-by-security-admin.txt"; then`
- `scripts/03-verify-archive.sh` line 33: `if aws s3api delete-object --bucket "$bucket" --key "$key" 2>&1 | tee "${EVIDENCE_DIR}/delete-by-workload-admin.txt"; then`
- `scripts/03-verify-archive.sh` line 40: `| tee "${EVIDENCE_DIR}/validate-logs.txt"`
- `scripts/04-drill-setup.sh` line 28: `} | tee "${EVIDENCE_DIR}/drill-capabilities.txt"`
- `scripts/05-posture-baseline.sh` line 13: `| tee "${EVIDENCE_DIR}/posture/${phase}.json" | python3 -c 'import json, sys; print(len(json.load(sys.stdin)["Findings"]), "open findings")'`
- `scripts/07-drill-attack.sh` line 11: `echo "FIRST ATTACKER ACTION AT $(stamp)" | tee "${EVIDENCE_DIR}/first-action.txt"`
- `scripts/07-drill-attack.sh` line 21: `echo "LAST ATTACKER ACTION AT $(stamp)" | tee -a "${EVIDENCE_DIR}/first-action.txt"`
- `scripts/08-contain.sh` line 9: `"$PY" -m detect_respond contain --role "$DRILL_ROLE" --user "$DRILL_USER" ${mode[@]+"${mode[@]}"} | tee -a "${EVIDENCE_DIR}/containment.txt"`
- `scripts/08-contain.sh` line 11: `echo "CONTAINED AT $(stamp)" | tee -a "${EVIDENCE_DIR}/containment.txt"`
- `scripts/09-collect-and-measure.sh` line 15: `"$PY" -m detect_respond drill --archive "${EVIDENCE_DIR}/archive" ${alerts[@]+"${alerts[@]}"} | tee "${EVIDENCE_DIR}/timeline.txt"`
- `scripts/10-teardown.sh` line 27: `echo "EXCEPTION REMOVED AT $(stamp)" | tee -a "${EVIDENCE_DIR}/containment.txt"`

#### `date`

`date`: prints the current date and time. Used for: time stamps in utc.

Flags used:

- `-u`: use UTC (the world clock) instead of the local time zone.

Every use:

- `scripts/03-verify-archive.sh` line 9: `marker="archive-check-$(date -u +%s)"`
- `scripts/lib.sh` line 20: `log() { printf '%s %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }`
- `scripts/lib.sh` line 49: `stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }`

#### `sleep`

`sleep`: waits for a number of seconds. Used for: pause between polls.

Every use:

- `scripts/03-verify-archive.sh` line 20: `log "nothing yet (attempt ${attempt} of 20)"; sleep 60`

#### `mkdir`

`mkdir`: creates a folder. Used for: make the evidence and build folders.

Flags used:

- `-p`: create the folder and any missing parents, and do not fail if it already exists.

Every use:

- `Makefile` line 63: `mkdir -p $(BUILD)`
- `scripts/03-verify-archive.sh` line 5: `mkdir -p "$EVIDENCE_DIR"`
- `scripts/04-drill-setup.sh` line 6: `mkdir -p "$EVIDENCE_DIR"`
- `scripts/05-posture-baseline.sh` line 9: `mkdir -p "${EVIDENCE_DIR}/posture"`
- `scripts/07-drill-attack.sh` line 6: `mkdir -p "$EVIDENCE_DIR"`
- `scripts/08-contain.sh` line 6: `mkdir -p "$EVIDENCE_DIR"`
- `scripts/09-collect-and-measure.sh` line 7: `mkdir -p "${EVIDENCE_DIR}/archive"`

#### `rm`

`rm`: removes files. Used for: clean up.

Flags used:

- `-rf`: remove folders and everything below them (`-r`) without asking (`-f`).
- `-f`: do not complain if the file does not exist.

Every use:

- `Makefile` line 126: `rm -rf $(VENV) $(BUILD) .pytest_cache .mypy_cache .ruff_cache .coverage .import_linter_cache evidence \`
- `scripts/04-drill-setup.sh` line 9: `sed -i.bak 's/^enable_drill .*/enable_drill        = true/' "${WORKLOAD_ENV}/sandbox.auto.tfvars" && rm -f "${WORKLOAD_ENV}/sandbox.auto.tfvars.bak"`
- `scripts/10-teardown.sh` line 10: `rm -f "${SECURITY_ENV}/sandbox.auto.tfvars"`
- `scripts/10-teardown.sh` line 26: `rm -f "${WORKLOAD_ENV}/sandbox.auto.tfvars"`

#### `cat`

`cat`: prints files (or, with `>` and a here-document, writes one). Used for: print or write files.

Every use:

- `scripts/01-deploy-security.sh` line 10: `cat > "${SECURITY_ENV}/sandbox.auto.tfvars" <<TFVARS`
- `scripts/02-deploy-workload.sh` line 11: `cat > "${WORKLOAD_ENV}/sandbox.auto.tfvars" <<TFVARS`

#### `printf`

`printf`: prints text from a format string; unlike `echo` its behavior is the same everywhere. Used for: print formatted lines.

Every use:

- `scripts/06-honeytoken.sh` line 9: `printf 'honeytoken_access_key_id = "%s"\n' "$key_id" >> "${WORKLOAD_ENV}/sandbox.auto.tfvars"`
- `scripts/07-drill-attack.sh` line 23: `printf '%s\n' "$ak" > "${EVIDENCE_DIR}/.session-key-id"`
- `scripts/lib.sh` line 20: `log() { printf '%s %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }`
- `scripts/lib.sh` line 21: `die() { printf 'error: %s\n' "$*" >&2; exit 1; }`

#### `dirname`

`dirname`: prints the folder part of a path. Used for: find the script's own folder.

Every use:

- `scripts/01-deploy-security.sh` line 5: `source "$(dirname "$0")/lib.sh"`
- `scripts/02-deploy-workload.sh` line 5: `source "$(dirname "$0")/lib.sh"`
- `scripts/03-verify-archive.sh` line 4: `source "$(dirname "$0")/lib.sh"`
- `scripts/04-drill-setup.sh` line 4: `source "$(dirname "$0")/lib.sh"`
- `scripts/05-posture-baseline.sh` line 6: `source "$(dirname "$0")/lib.sh"`
- `scripts/06-honeytoken.sh` line 4: `source "$(dirname "$0")/lib.sh"`
- `scripts/07-drill-attack.sh` line 5: `source "$(dirname "$0")/lib.sh"`
- `scripts/08-contain.sh` line 5: `source "$(dirname "$0")/lib.sh"`
- `scripts/09-collect-and-measure.sh` line 6: `source "$(dirname "$0")/lib.sh"`
- `scripts/10-teardown.sh` line 5: `source "$(dirname "$0")/lib.sh"`
- `scripts/lib.sh` line 9: `ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"`

#### `seq`

`seq`: prints a sequence of numbers. Used for: count attempts.

Every use:

- `scripts/03-verify-archive.sh` line 16: `for attempt in $(seq 1 20); do`

#### `install`

`install`: copies files or, with `-d`, creates folders, setting permissions in one step. Used for: create a directory with permissions.

Every use:

- `Makefile` line 15: `.PHONY: help install fmt lint test test-policy test-e2e audit plan check validate fixtures demo-drill review \`

#### `touch`

`touch`: creates an empty file or updates its modification time. Used for: create the stamp file.

Every use:

- `Makefile` line 25: `touch $@`

#### `pwd`

`pwd`: prints the current folder. Used for: resolve the repository root.

Every use:

- `scripts/lib.sh` line 9: `ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"`

#### `cd`

`cd`: changes the current folder. Used for: move into a folder in a sub-shell.

Every use:

- `scripts/lib.sh` line 9: `ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"`

#### `command`

`command`: a shell built-in; `command -v name` prints where `name` would be found and succeeds only if it exists. Used for: find which python exists.

Flags used:

- `-v`: print where the program is, and exit with an error if there is none.

Every use:

- `Makefile` line 3: `PYTHON ?= $(shell command -v python3.13 || command -v python3.12 || command -v python3)`
- `Makefile` line 3: `PYTHON ?= $(shell command -v python3.13 || command -v python3.12 || command -v python3)`
- `Makefile` line 3: `PYTHON ?= $(shell command -v python3.13 || command -v python3.12 || command -v python3)`
- `scripts/lib.sh` line 24: `for tool in "$@"; do command -v "$tool" >/dev/null 2>&1 || die "$tool is required"; done`

## Try it yourself

```bash
date -u +%Y-%m-%dT%H:%M:%SZ
```

Expect the current UTC time such as `2026-10-27T11:45:46Z`.

```bash
printf '2026-10-22 11:20:01       1234 AWSLogs/a/b.json.gz\n2026-10-22 11:21:01       99 AWSLogs/a/c.json.gz\n' | awk '{print $4}' | sed -n '1p'
```

Expect `AWSLogs/a/b.json.gz`: the path column of the first line.

```bash
printf 'abcdefghij\n' | cut -c1-4; printf '1\n2\n3\n' | tail -n 1
```

Expect `abcd` and then `3`.

```bash
printf 'k = 1\nenable_drill = false\n' > /tmp/t.tfvars
sed -i.bak 's/^enable_drill .*/enable_drill        = true/' /tmp/t.tfvars && rm -f /tmp/t.tfvars.bak
cat /tmp/t.tfvars; rm /tmp/t.tfvars
```

Expect `k = 1` and `enable_drill        = true`: the second line was rewritten in place.

```bash
make help | head -n 3
```

Expect `attack`, `audit` and `check`, each followed by its description.

## Mistakes people make

- Using plain `sed -i` in a script. macOS and Linux disagree about its argument; `-i.bak` works on both.
- Treating a failed `grep -q` as an error. Exit 1 only means "no match". Under `set -e` the script handles it with `if grep -q ...; then`.
- Cutting a pipeline's exit code. `cmd | tail -n 1` returns the exit code of the last program unless `pipefail` is on.
- Hiding output with `tail` or `cut` while debugging. Remove them to see everything.
- Using `date -d` (GNU) on macOS. The scripts try the macOS form first and fall back: `date -u -v-1H ... || date -u -d '1 hour ago' ...`.

## Check yourself

1. What does the `Z` in `%H:%M:%SZ` mean? *It is a literal letter: the time is UTC.*
2. What does `awk '{print $4}'` do? *Prints the fourth column of every line.*
3. What does `sed -n '1p'` print? *Only the first line.*
4. What does `tee` do? *Copies its input to the screen and to a file.*
5. Why `sed -i.bak`? *It edits in place and works the same on macOS and Linux.*

## Further reading

- GNU coreutils (`date`, `seq`, `sleep`, `tee`, `tail`, `head`, `cut`, `sort`): <https://www.gnu.org/software/coreutils/manual/coreutils.html>
- GNU sed: <https://www.gnu.org/software/sed/manual/sed.html>; GNU awk: <https://www.gnu.org/software/gawk/manual/gawk.html>; GNU grep: <https://www.gnu.org/software/grep/manual/grep.html>
