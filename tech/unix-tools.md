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
