# ShellCheck

## What it is

ShellCheck is a command-line **linter for shell scripts**: it reads a script and reports bugs and risky habits (a missing quote, a variable that is never used, a command that behaves differently than it looks). This repository was verified with **ShellCheck 0.11.0**, and CI uses the version on the GitHub runner.

## Why this repository uses it

The scripts under `scripts/` run against a real cloud account. A shell script fails in quiet ways: an unquoted variable splits on spaces, a failed command in the middle of a pipeline is ignored. ShellCheck catches these before they cost money or delete the wrong thing.

## Where it appears

| Path | What it does with ShellCheck |
| --- | --- |
| `Makefile` | `make lint` runs `shellcheck scripts/*.sh` |
| `.shellcheckrc` | two options for following `source` lines |
| `scripts/*.sh` | the files it checks; a few lines carry `# shellcheck` directives |

## How it works underneath

ShellCheck parses the script the way bash would, then applies a few hundred rules. Each rule has a code such as `SC2086` ("double quote to prevent word splitting"). A **directive** is a special comment (`# shellcheck disable=SC2034`) that changes ShellCheck's behavior for the file or the next command.

## Walkthrough of this repository's use

ShellCheck is a **static analyzer**: it reads a shell script as text, without running it, and reports lines that are probably wrong or fragile. Each finding has a code that starts with `SC` and a number (for example `SC2086`), a severity, the line, and an explanation. The repository uses ShellCheck in three places, and each one is shown below with every line.

From `.shellcheckrc` (lines 1 to 2):

```text
external-sources=true
source-path=SCRIPTDIR
```

`.shellcheckrc` is ShellCheck's settings file. It is read from the repository's top folder every time ShellCheck runs. A line is `name=value`.

- `external-sources=true`: every numbered script begins with `source "$(dirname "$0")/lib.sh"`, which loads the helper file. By default ShellCheck does not read files that a script loads, so it cannot know which functions and variables exist and would warn about them. This setting allows it to follow the `source` line and read the helper.
- `source-path=SCRIPTDIR`: tells ShellCheck where to look for the file named in a `source` line. `SCRIPTDIR` is a special value that means "the folder of the script being checked", which is exactly where `lib.sh` lives.

From `scripts/lib.sh` (line 2):

```bash
# shellcheck disable=SC2034
```

This is a **directive**: a comment that starts with `shellcheck` is an instruction to ShellCheck, not text for people. `disable=SC2034` switches off one rule for the rest of the file. `SC2034` means "this variable appears to be unused". `lib.sh` assigns 10 variables (`ROOT`, `EVIDENCE_DIR`, `SECURITY_ENV`, `WORKLOAD_ENV`, `REGION`, `TF`, `PY`, `DRILL_ROLE`, `DRILL_USER`, `SESSION_NAME`) that are used only by the scripts that load it; when ShellCheck reads `lib.sh` on its own, it sees assignments that nothing reads, and would warn about every one. The directive sits on the second line of the file, directly under the shebang, so it applies to the whole file. It is the only directive in the repository: no script silences anything else.

From `Makefile` (line 46):

```make
	shellcheck scripts/*.sh
```

`make lint` runs ShellCheck on every script: `shellcheck scripts/*.sh`. The `*` is a **wildcard**: before `shellcheck` starts, the shell replaces `scripts/*.sh` with the list of all matching file names, here 11 files: `01-deploy-security.sh`, `02-deploy-workload.sh`, `03-verify-archive.sh`, `04-drill-setup.sh`, `05-posture-baseline.sh`, `06-honeytoken.sh`, `07-drill-attack.sh`, `08-contain.sh`, `09-collect-and-measure.sh`, `10-teardown.sh`, `lib.sh`. ShellCheck exits with a non-zero code if any rule fires, so `make` stops and `make lint` fails; it prints nothing and exits 0 when all is well. The Python helper script in the same folder (`make_drill_fixtures.py`) is not a shell script; it is checked by [ruff](ruff.md) and [mypy](mypy.md) instead.

## Try it yourself

```bash
shellcheck --version | sed -n 2p
```

Expect `version: 0.11.0` (or yours).

```bash
shellcheck scripts/*.sh && echo clean
```

Expect `clean`.

```bash
printf '#!/bin/bash\nname="a b"\nrm -rf $name\n' > /tmp/bad.sh; shellcheck /tmp/bad.sh
```

Expect `SC2086 (info): Double quote to prevent globbing and word splitting.` and the suggestion `rm -rf "$name"`. The unquoted `$name` would be split into two words.

```bash
shellcheck --list-optional | sed -n 1,2p
```

Expect `name:    add-default-case` and its description: optional checks that are off by default.

## Mistakes people make

- Disabling a rule to make it quiet. Fix the script. In this repository the only directive is for variables used by other files.
- Not following `source`d files, so every use of a library function looks like an unknown command.
- Assuming a clean ShellCheck means the script is correct. It checks style and common bugs, not your logic.

## Check yourself

1. What does ShellCheck do to a script? *Reads it and reports bugs and risky patterns without running it.*
2. What is `SC2086`? *Unquoted variable: word splitting and globbing risk.*
3. Why `external-sources=true`? *So it can read the `lib.sh` the scripts source.*
4. Why is `SC2034` disabled in `lib.sh`? *The variables are used by other files that source it.*
5. Which Make target runs it? *`make lint`.*

## Further reading

- ShellCheck: <https://www.shellcheck.net/> and the wiki with every rule: <https://www.shellcheck.net/wiki/> (version 0.11.0)
