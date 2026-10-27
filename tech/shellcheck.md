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

From `.shellcheckrc`:

```text
external-sources=true
source-path=SCRIPTDIR
```

Every runbook script begins with `source "$(dirname "$0")/lib.sh"`. By default ShellCheck does not read the file you `source`, so it cannot know which functions exist. `external-sources=true` allows it to follow, and `source-path=SCRIPTDIR` says "look in the folder of the script being checked".

From `scripts/lib.sh`:

```bash
# shellcheck disable=SC2034
```

`SC2034` means "this variable appears unused". `lib.sh` sets variables (`REGION`, `ENV_DIR`, ...) that only the scripts that source it use, so ShellCheck cannot see the use. The directive is on the second line of the file and applies to the whole file. Nothing else in `scripts/` is silenced.

From `Makefile`:

```make
	shellcheck scripts/*.sh
```

The shell expands `scripts/*.sh` to the list of files. The command exits non-zero if any rule fires, and `make lint` stops.

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
