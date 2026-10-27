# GNU Make

## What it is

Make is a command-line tool that runs named recipes from a file called `Makefile`. You type `make lint` and Make finds the **target** called `lint` in the file and runs the shell commands listed under it. Make also knows about **dependencies**: a target can say "I need these other targets or files first". This repository uses the Make that ships with macOS and Linux (**GNU Make 3.81 or newer**; 3.81 is what macOS has).

## Why this repository uses it

The project rule is that a reader needs only a few commands. `make validate`, `make lint`, `make test` and `make demo-drill` hide the long command lines (the right Python, the right flags, placeholder credentials) behind short names, and CI runs the same names, so "works on my machine" and "works in CI" are the same thing. The Makefile also splits the targets in two groups: the ones that work offline (`validate`, `lint`, `test`, `demo-drill`) and the ones that need two sandbox accounts (`up`, `run`, `attack`, `respond`, `measure`, `down`).

## Where it appears

| Path | What it does with Make |
| --- | --- |
| `Makefile` | every target of the project |
| `.github/workflows/ci.yml` | calls `make lint`, `make test`, `make validate`, `make demo-drill` and others |

## How it works underneath

Make reads the whole file, then builds the target you asked for. A **rule** has the shape:

```text
target: dependencies
<TAB>command
```

Each command line must start with a real tab character. Make runs each line in its own shell. If a command exits with a non-zero code, Make stops and reports an error. A **variable** (`PY := ...`) is a text substitution; `$(PY)` pastes its value. For a *file* target Make compares times: if the target file is newer than all its dependencies it is skipped. A **phony** target is a name for an action, not a file.

## Walkthrough of this repository's use

This is the whole `Makefile`, every line, in file order. Read this paragraph first, because every line uses these ideas.

**What `make` does.** `make` is a program that reads the file called `Makefile` in the current folder. The file is a list of **rules**. A rule has a **target** (a name, written before the colon), optional **prerequisites** (what must be done first, written after the colon) and a **recipe** (the shell commands that do the work, written on the lines below, each starting with a **tab character**, not spaces). `make lint` means "run the recipe of the target `lint`, after making sure its prerequisites are done". A **shell** is the program that reads command lines such as `ls -l`; `make` hands each recipe line to the shell, and **each line runs in its own new shell**, so a `cd` on one line does not carry over to the next. If a command ends with a failure (a non-zero **exit code**, the number every program returns when it finishes; 0 means success), `make` stops and reports an error, so a failing check stops the recipe.

**Variables.** A line `NAME := value` stores text under a name. `$(NAME)` pastes it wherever it is used. `:=` computes the value once, right there. `?=` stores the value only if the name is not already set, so you can override it: `TF=tofu make plan` runs the same recipes with `tofu` in place of `terraform`. `$(shell command)` runs a command and pastes its output. `$(CURDIR)` is a built-in variable holding the current folder. `$@` inside a recipe is the name of the target being built. A `$` that the shell must see is written `$$`. A **comment** starts with `#`.

**Phony targets.** A target normally names a *file*; `make` rebuilds the file only if a prerequisite is newer. A target that names an *action* (such as `lint`) is listed after `.PHONY`, so `make` runs it every time even if a file with that name exists.

From `Makefile` (lines 1 to 2):

```make
# make validate | lint | test | check | demo-drill   work offline, with no account and no credentials (make help lists all)
# make up | run | attack | respond | measure | down   need two sandbox accounts and credentials (see docs/RUNBOOK.md)
```

Two comment lines at the top. They tell the reader which targets work **offline** with no cloud account (`validate`, `lint`, `test`, `check`, `demo-drill`) and which need two sandbox accounts and credentials (`up`, `run`, `attack`, `respond`, `measure`, `down`), and that `make help` lists everything.

From `Makefile` (lines 3 to 4):

```make
PYTHON ?= $(shell command -v python3.13 || command -v python3.12 || command -v python3)
TF ?= terraform
```

`PYTHON ?=` picks the interpreter used to create the environment: `command -v NAME` prints the path of a program if it exists and nothing if not, and `||` means "if the previous command failed, try the next", so the result is the first of `python3.13`, `python3.12`, `python3` that is installed. `TF ?= terraform` names the Terraform program; both can be overridden from the command line.

From `Makefile` (lines 5 to 7):

```make
VENV := .venv
PY := $(VENV)/bin/python
STAMP := $(VENV)/.installed
```

`VENV` is the folder of the virtual environment. `PY` is the Python inside it, so every recipe runs the project's own Python and its own libraries. `STAMP` is the stamp file explained at the rule below.

From `Makefile` (lines 8 to 9):

```make
ENVS := security workload
BUILD := build
```

`ENVS` lists the two Terraform environments, one per account: `security` (the archive) and `workload` (the trail, detections and the drill). `BUILD` is the output folder. Terraform and JSON are explained in [terraform.md](terraform.md) and [json.md](json.md).

From `Makefile` (lines 10 to 11):

```make
# Placeholder values only, so the provider can start; plan_only makes it skip every call to AWS.
OFFLINE := env -u AWS_PROFILE AWS_ACCESS_KEY_ID=plan-only AWS_SECRET_ACCESS_KEY=plan-only AWS_EC2_METADATA_DISABLED=true
```

`OFFLINE` is a command prefix. `env` runs a command with a changed **environment** (the set of named values, called **environment variables**, that every program receives from the program that started it). `-u AWS_PROFILE` removes the variable `AWS_PROFILE`, so a real profile on your machine can never be used by accident. The next two settings give the AWS variables placeholder values (`plan-only`): the provider insists on *some* credentials before it starts, but the plan never sends them anywhere ([terraform-aws-provider.md](terraform-aws-provider.md)). `AWS_EC2_METADATA_DISABLED=true` stops it from asking a cloud server's metadata address for credentials.

From `Makefile` (line 12):

```make
DR := $(PY) -m detect_respond
```

`DR` is shorthand for running the project's own tool: `python -m detect_respond` runs the package `detect_respond` ([python.md](python.md)).

From `Makefile` (line 13):

```make
REHEARSAL := fixtures/drill
```

`REHEARSAL` is the folder that holds the synthetic audit archive of the rehearsal (`fixtures/drill`), used by several targets.

From `Makefile` (lines 15 to 16):

```make
.PHONY: help install fmt lint test test-policy test-e2e audit plan check validate fixtures demo-drill review \
        up run attack respond measure down clean
```

`.PHONY` lists the targets that are actions and not files, so they always run. The trailing backslash `\` joins this line to the next, which only keeps the line short.

From `Makefile` (lines 18 to 19):

```make
help: ## list the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | sort
```

`make help` lists the targets. A target line that ends with `## some text` carries its own help text. The recipe has one line: the `@` at the start stops `make` from printing the command before running it. `grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST)` keeps the lines of the Makefile that look like `target: ... ## text` (`-E` selects extended patterns; `^` is the start of a line; `[a-z-]+` is one or more lowercase letters or hyphens). `sed -E 's/:.*## /\t/'` replaces everything from the first colon up to `## ` with a tab, leaving `target<tab>text`. `sort` puts the lines in order. The `|` between the commands is a **pipe**: it feeds the output of one program into the next ([unix-tools.md](unix-tools.md)).

From `Makefile` (lines 21 to 25):

```make
$(STAMP): requirements-dev.lock pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -q --require-hashes -r requirements-dev.lock
	$(VENV)/bin/pip install -q --no-deps -e .
	touch $@
```

This rule builds a **file**, not an action. The target is `$(STAMP)`, which is `.venv/.installed`. Its prerequisites are the lock file and `pyproject.toml`: if either is newer than the stamp, the recipe runs again, otherwise `make` does nothing. That makes every other target that needs the environment cheap to repeat. The recipe has four lines:

- `$(PYTHON) -m venv $(VENV)` creates a **virtual environment**: a private folder (`.venv/`) holding a copy of the Python interpreter and its own set of installed libraries, so this project's libraries cannot collide with any other project's. `-m venv` means "run the module named `venv` that ships with Python".
- `$(VENV)/bin/pip install -q --require-hashes -r requirements-dev.lock` installs every library from the lock file into the environment. `pip` is Python's package installer. `-q` is quiet. `-r FILE` reads the list of requirements from a file. `--require-hashes` makes `pip` refuse any library whose downloaded file does not match the fingerprint recorded in the lock file ([pip.md](pip.md)).
- `$(VENV)/bin/pip install -q --no-deps -e .` installs *this project* in **editable** mode (`-e`): the environment points at the source folder instead of copying it, so edits take effect at once. `--no-deps` stops `pip` from looking for dependencies, because the previous line already installed all of them exactly.
- `touch $@` creates the empty stamp file `.venv/.installed`, which is how `make` remembers the work is done.

From `Makefile` (line 27):

```make
install: $(STAMP) ## create .venv from the lock file
```

`install` only has a prerequisite and no recipe: asking for `install` makes sure `$(STAMP)` exists.

From `Makefile` (lines 29 to 33):

```make
fmt: $(STAMP) ## apply ruff, terraform fmt and opa fmt
	$(VENV)/bin/ruff check --fix .
	$(VENV)/bin/ruff format .
	$(TF) fmt -recursive infra
	opa fmt -w policy
```

`fmt` is the "fix it for me" twin of `lint`. `ruff check --fix .` applies the fixes the linter can make by itself, `ruff format .` rewrites the files in the standard layout, `$(TF) fmt -recursive infra` formats the Terraform files, and `opa fmt -w policy` formats the policy files (`-w` means "write the result back to the file").

From `Makefile` (lines 35 to 46):

```make
lint: $(STAMP) ## ruff, mypy, import rules, terraform fmt, tflint, checkov, opa check, shellcheck
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .
	$(VENV)/bin/mypy
	$(VENV)/bin/lint-imports
	$(TF) fmt -check -recursive infra
	tflint --init
	tflint --recursive --config $(CURDIR)/.tflint.hcl
	checkov -d infra --framework terraform --quiet --compact
	opa fmt --list --fail policy
	opa check --strict policy
	shellcheck scripts/*.sh
```

`lint` first needs `$(STAMP)` (the virtual environment, explained above). The recipe is a list of independent checkers; each is explained in its own note. If any one fails, `make` stops.

- `$(VENV)/bin/ruff check .` runs the linter on the whole repository (`.` is the current folder) ([ruff.md](ruff.md)).
- `$(VENV)/bin/ruff format --check .` asks the formatter whether any file *would* change, and fails if so, without changing anything.
- `$(VENV)/bin/mypy` runs the type checker with the file list from `pyproject.toml` ([mypy.md](mypy.md)).
- `$(VENV)/bin/lint-imports` checks the import rules ([import-linter.md](import-linter.md)).
- `$(TF) fmt -check -recursive infra` checks that every Terraform file under `infra/` is formatted (`-check` means "report, do not rewrite"; `-recursive` descends into sub-folders) ([terraform.md](terraform.md)).
- `tflint --init` downloads the plug-ins listed in `.tflint.hcl`, and `tflint --recursive --config $(CURDIR)/.tflint.hcl` lints every Terraform folder with that configuration ([tflint.md](tflint.md)).
- `checkov -d infra --framework terraform --quiet --compact` scans `infra/` for security weaknesses ([checkov.md](checkov.md)).
- `opa fmt --list --fail policy` lists policy files that are not formatted and fails if there are any; `opa check --strict policy` parses the policy and reports mistakes such as unused variables ([opa-rego.md](opa-rego.md)).
- `shellcheck scripts/*.sh` lints every shell script in `scripts/`; the `*` is a **wildcard** that the shell expands to all matching file names ([shellcheck.md](shellcheck.md)).

From `Makefile` (lines 48 to 50):

```make
test: $(STAMP) test-policy ## unit tests with coverage, and the policy tests
	$(PY) -m pytest tests/unit --cov --cov-report=term
	$(PY) -m coverage report --include='src/*/domain/*,src/*/application/*' --fail-under=95
```

`test` needs the environment and `test-policy` first. `$(PY) -m pytest tests/unit --cov --cov-report=term` runs the unit tests and measures coverage; `--cov` with no value uses the settings in `pyproject.toml`, and `--cov-report=term` prints the table in the terminal ([pytest.md](pytest.md), [coverage.md](coverage.md)). `$(PY) -m coverage report --include='src/*/domain/*,src/*/application/*' --fail-under=95` then prints the table for the domain and application folders only, and fails if the total is below 95 percent. The pattern is in single quotes so the shell passes the `*` to the program instead of expanding it.

From `Makefile` (lines 52 to 53):

```make
test-policy: ## opa unit tests: a deny and an allow case for every rule
	opa test policy
```

`test-policy` runs the unit tests of the policy files with `opa test policy` ([opa-rego.md](opa-rego.md)). It has no prerequisite, because OPA needs no Python environment. The comment after `##` is its help text.

From `Makefile` (lines 55 to 57):

```make
# Needs terraform. Runs the whole offline pipeline through make.
test-e2e: $(STAMP) ## the plan-and-check pipeline through make, as a reader runs it
	$(PY) -m pytest tests/e2e -m e2e
```

The comment says `test-e2e` needs Terraform and runs the whole offline pipeline through `make`. `-m e2e` selects the tests that carry the marker `e2e`, the ones that the default run skips ([pytest.md](pytest.md)).

From `Makefile` (lines 59 to 60):

```make
audit: $(STAMP) ## check the locked dependencies for known vulnerabilities
	$(VENV)/bin/pip-audit --no-deps --disable-pip -r requirements-dev.lock
```

`audit` checks the pinned libraries against public lists of known vulnerabilities ([pip-audit.md](pip-audit.md)). `--no-deps` and `--disable-pip` tell `pip-audit` to trust the lock file as the complete list instead of resolving dependencies again, and `-r requirements-dev.lock` names that file. It needs network access.

From `Makefile` (lines 62 to 69):

```make
plan: $(STAMP) ## terraform plan of both environments with no credentials: build/<env>.json
	mkdir -p $(BUILD)
	@for env in $(ENVS); do \
	  dir=infra/environments/$$env; \
	  $(TF) -chdir=$$dir init -backend=false -input=false >/dev/null && \
	  $(OFFLINE) $(TF) -chdir=$$dir plan -var-file=plan-only.tfvars -out=$(CURDIR)/$(BUILD)/$$env.tfplan -input=false -lock=false -no-color | grep -E "^Plan:|Error" && \
	  $(TF) -chdir=$$dir show -json $(CURDIR)/$(BUILD)/$$env.tfplan > $(BUILD)/$$env.json || exit 1; \
	done
```

`plan` needs the environment. The recipe creates the output folder and then runs one shell loop over both environments.

- `mkdir -p $(BUILD)` creates the output folder; `-p` means "also create parents, and do nothing if it already exists".
- `@for env in $(ENVS); do ... done` is a shell **loop**: the commands between `do` and `done` run once for each word in the list, with the variable `env` set to that word (`security`, then `workload`). `make` would treat `$env` as one of its own variables, so a shell variable is written `$$env`; `make` turns `$$` into a single `$` before the shell sees it. All the lines are joined by `\` into one command, because each recipe line would otherwise run in its own shell and lose the variable. The `@` hides the command text.
- `dir=infra/environments/$$env;` stores the folder of the current environment.
- `$(TF) -chdir=$$dir init -backend=false -input=false >/dev/null && \` prepares the folder. `-chdir=DIR` makes Terraform behave as if started inside it; `-backend=false` skips remote state; `-input=false` forbids questions. `>/dev/null` throws the output away (`/dev/null` is a special file that discards everything written to it). `&&` means "run the next command only if this one succeeded".
- `$(OFFLINE) $(TF) -chdir=$$dir plan -var-file=plan-only.tfvars -out=... -input=false -lock=false -no-color | grep -E "^Plan:|Error" && \` builds the plan with the placeholder environment. `-var-file` reads variable values from a file; `-out=FILE` saves the plan as `build/<env>.tfplan`; `-lock=false` skips the state lock; `-no-color` removes colour codes so `grep` can match plain text. `grep -E "^Plan:|Error"` keeps only the summary line (`Plan: N to add, ...`) or an error line.
- `$(TF) -chdir=$$dir show -json ... > $(BUILD)/$$env.json || exit 1; \` writes the saved plan as JSON text into `build/<env>.json` (`>` sends output into a file). `|| exit 1` ends the whole loop with an error if any step of that environment failed; `done` closes the loop.

From `Makefile` (lines 71 to 76):

```make
check: $(STAMP) ## policy rules on both plans, and the rules in the plan equal detections/ (make plan first)
	@for env in $(ENVS); do \
	  echo "== policy rules on $$env"; \
	  opa eval --fail-defined --format pretty -d policy -i $(BUILD)/$$env.json 'data.detection.deny[_]' || exit 1; \
	done
	$(DR) audit-rules --plan $(BUILD)/workload.json
```

`check` runs the policy rules on **both** plans and then the rule audit; the help text reminds you to run `make plan` first. The loop has the same shape as in `plan`: for each environment it prints a heading with `echo` and runs `opa eval --fail-defined --format pretty -d policy -i $(BUILD)/$$env.json 'data.detection.deny[_]'`, which asks OPA for every message in the set `deny` (`-d policy` loads the policy folder, `-i FILE` supplies the input; `--fail-defined` makes the command fail if there is any message) ([opa-rego.md](opa-rego.md)). `|| exit 1` stops at the first failure. The last line, `$(DR) audit-rules --plan $(BUILD)/workload.json`, checks that the detection rules in the plan are exactly the files in `detections/`.

From `Makefile` (lines 78 to 79):

```make
fixtures: ## regenerate fixtures/ (the synthetic archive and posture findings); the tests check they are current
	$(PY) scripts/make_drill_fixtures.py fixtures
```

`fixtures` regenerates the synthetic audit archive and the posture findings. `$(PY) scripts/make_drill_fixtures.py fixtures` runs the helper script with the output folder as its argument. The tests check that the committed fixtures equal what the script produces.

From `Makefile` (lines 81 to 92):

```make
# The lesson's step 5 on a rehearsal archive: detect, rebuild the timeline from the logs only, measure, verify the archive.
demo-drill: $(STAMP) ## replay the rehearsal archive: alerts, timeline, time to detect and contain, archive integrity
	@echo "== detections over the archive (D1, D2 and D4 must fire)"
	@$(DR) scan --archive $(REHEARSAL) --expect D1,D2,D4 | tail -n 1
	@echo "== the timeline, from the logs only"
	@$(DR) drill --archive $(REHEARSAL) --alerts $(REHEARSAL)/alerts.json
	@echo "== the archive against its digests"
	@$(DR) verify-archive --archive $(REHEARSAL)
	@echo "== the posture baseline"
	@$(DR) posture --findings fixtures/posture --accepted fixtures/posture/accepted.json
	@echo "== containment, as a dry run"
	@$(DR) contain --access-key-id AKIADRILLEXAMPLE0001 | cut -c1-160
```

`demo-drill` replays the whole rehearsal offline. The comment above it names the steps: detect, rebuild the timeline from the logs only, measure, verify the archive. Every line starts with `@`, which hides the command text so only the headings and results show. `echo "== ..."` prints a heading. Then, in order:

- `$(DR) scan --archive $(REHEARSAL) --expect D1,D2,D4 | tail -n 1` runs every detection over the archive and fails if D1, D2 or D4 does not fire; `| tail -n 1` keeps only the last line of the output, the summary ([unix-tools.md](unix-tools.md)).
- `$(DR) drill --archive $(REHEARSAL) --alerts $(REHEARSAL)/alerts.json` rebuilds the timeline of the attacker's session and prints the time to detect and the time to contain.
- `$(DR) verify-archive --archive $(REHEARSAL)` checks the log files against their digest files.
- `$(DR) posture --findings fixtures/posture --accepted fixtures/posture/accepted.json` prints the posture baseline table.
- `$(DR) contain --access-key-id AKIADRILLEXAMPLE0001 | cut -c1-160` prints the containment plan as a **dry run** (nothing is sent anywhere); `cut -c1-160` keeps the first 160 characters of each line.

From `Makefile` (lines 94 to 95):

```make
review: $(STAMP) ## regenerate docs/REHEARSAL_REVIEW.md from the rehearsal archive
	$(DR) review --archive $(REHEARSAL) --alerts $(REHEARSAL)/alerts.json --output docs/REHEARSAL_REVIEW.md
```

`review` rewrites `docs/REHEARSAL_REVIEW.md` from the rehearsal archive (`--output FILE` writes the result there).

From `Makefile` (lines 97 to 102):

```make
validate: $(STAMP) plan ## terraform fmt and validate, credential-free plans, the rules, the replay, the review is current
	$(TF) fmt -check -recursive infra
	@for env in $(ENVS); do $(TF) -chdir=infra/environments/$$env validate || exit 1; done
	$(MAKE) --no-print-directory check
	$(MAKE) --no-print-directory demo-drill
	$(DR) review --archive $(REHEARSAL) --alerts $(REHEARSAL)/alerts.json --check docs/REHEARSAL_REVIEW.md
```

`validate` is the one command that proves the offline work. Its prerequisites are the environment and `plan`. Then: `$(TF) fmt -check -recursive infra`; a loop that runs `$(TF) -chdir=infra/environments/$$env validate` for each environment (it checks that the configuration is consistent without contacting any cloud, and `|| exit 1` stops at the first failure); `$(MAKE) --no-print-directory check` and `... demo-drill` start `make` again, as **sub-makes** (`$(MAKE)` is the running `make` itself, and `--no-print-directory` removes noise); and the last line runs the review command with `--check`, which fails if the committed `docs/REHEARSAL_REVIEW.md` differs from a fresh one.

From `Makefile` (lines 104 to 106):

```make
up: ## deploy the archive to the security account, then the trail and detections to the workload account
	scripts/01-deploy-security.sh
	scripts/02-deploy-workload.sh
```

`up` runs two deploy scripts in order: first the archive in the security account, then the trail and detections in the workload account ([bash.md](bash.md)). They need credentials for two accounts.

From `Makefile` (lines 108 to 111):

```make
run: ## check the archive, plant the drill exception, take the posture baseline
	scripts/03-verify-archive.sh
	scripts/04-drill-setup.sh
	scripts/05-posture-baseline.sh before
```

`run` checks the archive, plants the drill exception and takes the posture baseline. `scripts/05-posture-baseline.sh before` passes the word `before` as the script's first argument.

From `Makefile` (lines 113 to 114):

```make
attack: ## play the attacker against the drill resources (write down the clock time it prints)
	scripts/07-drill-attack.sh
```

`attack` plays the attacker against the drill resources and prints the clock time of the first action.

From `Makefile` (lines 116 to 117):

```make
respond: ## contain from the evidence; add APPLY=--apply to change anything (a dry run by default)
	scripts/08-contain.sh $(APPLY)
```

`respond` contains the attacker from the evidence. `$(APPLY)` is a variable that is normally empty, so the script runs as a **dry run**. `make respond APPLY=--apply` sets the variable on the command line, and the script receives the word `--apply` and changes the account. The change only happens if you type it.

From `Makefile` (lines 119 to 120):

```make
measure: ## copy the archive out, verify it, rebuild the timeline, measure both times, write the review
	scripts/09-collect-and-measure.sh
```

`measure` copies the archive out, verifies it, rebuilds the timeline, measures both times and writes the review.

From `Makefile` (lines 122 to 123):

```make
down: ## remove the drill exception and delete the workload account's resources (the archive follows after its retention)
	scripts/10-teardown.sh
```

`down` removes the temporary exception and deletes the workload account's resources. The archive in the security account follows after its retention ends.

From `Makefile` (lines 125 to 127):

```make
clean:
	rm -rf $(VENV) $(BUILD) .pytest_cache .mypy_cache .ruff_cache .coverage .import_linter_cache evidence \
	  infra/environments/security/.terraform infra/environments/workload/.terraform
```

`clean` deletes everything the build created, so the next run starts from nothing. `rm -rf` removes files and folders without asking (`-r` descends into folders, `-f` ignores files that do not exist). The names are the virtual environment, the `build` folder, the caches of pytest, mypy, ruff and import-linter, the coverage data file, the collected `evidence` folder and Terraform's downloaded plug-ins in both environments. The trailing `\` continues the command on the next line.

## Try it yourself

```bash
make help | head -n 3
```

Expect `attack`, `audit` and `check`, each followed by its description.

```bash
make -n lint | head -n 3
```

`-n` prints the commands without running them. Expect `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .` and `.venv/bin/mypy`.

```bash
make -n install
```

Expect ``make: Nothing to be done for `install'.`` when `.venv/.installed` is newer than both `requirements-dev.lock` and `pyproject.toml`: the stamp logic at work. Run `touch requirements-dev.lock` and repeat; now Make prints the `python3.13 -m venv .venv` line it would run.

```bash
make -n plan | sed -n 1,3p
```

Expect `mkdir -p build`, then `for env in security workload; do \` and the line `dir=infra/environments/$env;`: Make turned `$$env` into `$env`.

```bash
TF=tofu make -n plan | grep -m1 init
```

Expect a line containing `tofu -chdir=$dir init -backend=false -input=false`: the override worked.

## Mistakes people make

- Using spaces instead of a tab before a command. Make reports `missing separator`. `.editorconfig` sets tabs for the Makefile.
- Writing `$env` in a recipe loop. Make would look for its own variable `env`; write `$$env`.
- Expecting `cd` on one line to affect the next line. Each line is a new shell; join with `;` or `&&`.
- Naming a target after a file that exists, so Make thinks it is up to date. That is why action targets are in `.PHONY`.
- Using a Make feature newer than 3.81. This Makefile avoids them on purpose, because macOS ships 3.81.

## Check yourself

1. What does `a: b` mean in a Makefile? *Target `a` needs `b` first.*
2. What does `$@` stand for? *The name of the current target.*
3. Why is a shell variable written `$$env` in a recipe? *Make converts `$$` into one `$`; a single `$` would be read by Make itself.*
4. Why does `lint` depend on `$(STAMP)`? *So the virtual environment exists before the checkers run.*
5. How do you make `make respond` change the account? *`make respond APPLY=--apply`.*

## Further reading

- GNU Make manual: <https://www.gnu.org/software/make/manual/make.html> (3.81 is the oldest supported version here)
