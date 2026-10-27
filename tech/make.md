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

From `Makefile`:

```make
PYTHON ?= $(shell command -v python3.13 || command -v python3.12 || command -v python3)
TF ?= terraform
VENV := .venv
PY := $(VENV)/bin/python
```

- `?=` sets a variable only if it is not already set, so `TF=tofu make plan` overrides it.
- `$(shell ...)` runs a shell command and uses its output: the first of `python3.13`, `python3.12`, `python3` that exists.
- `:=` evaluates the right side once, immediately.

From `Makefile`:

```make
ENVS := security workload
OFFLINE := env -u AWS_PROFILE AWS_ACCESS_KEY_ID=plan-only AWS_SECRET_ACCESS_KEY=plan-only AWS_EC2_METADATA_DISABLED=true
DR := $(PY) -m detect_respond
```

`ENVS` lists the two Terraform environments (one per account). `env` runs a command with a changed environment: `-u AWS_PROFILE` removes that variable, so a real profile on your laptop is never used, and the two `plan-only` values are placeholders so the AWS provider starts; no cloud call is made ([terraform-aws-provider.md](terraform-aws-provider.md)). `DR` is a shorthand for running the tool, so a target can say `$(DR) scan ...`.

From `Makefile`:

```make
help: ## list the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | sort
```

A comment starting `##` after a target is its help text. `@` at the start of a command line stops Make from printing the command before running it. `$(MAKEFILE_LIST)` is the Makefile's own name. The pipeline lists every target with its help text ([unix-tools.md](unix-tools.md)).

From `Makefile`:

```make
$(STAMP): requirements-dev.lock pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -q --require-hashes -r requirements-dev.lock
	$(VENV)/bin/pip install -q --no-deps -e .
	touch $@
```

A file target. `$(STAMP)` is `.venv/.installed`. If `requirements-dev.lock` or `pyproject.toml` is newer, Make rebuilds the venv; otherwise `make lint` skips the install. `touch $@` creates the stamp, and `$@` is "the target of this rule". The two `pip install` lines are explained in [pip.md](pip.md).

From `Makefile`:

```make
plan: $(STAMP) ## terraform plan of both environments with no credentials: build/<env>.json
	mkdir -p $(BUILD)
	@for env in $(ENVS); do \
	  dir=infra/environments/$$env; \
	  $(TF) -chdir=$$dir init -backend=false -input=false >/dev/null && \
```

A shell loop inside a recipe. Make would treat `$env` as one of its own variables, so a shell variable is written `$$env`: Make turns `$$` into a single `$` before the shell sees it. The backslashes join the lines into one command, because each line of a recipe would otherwise run in its own shell. `-chdir=$$dir` makes Terraform behave as if started in that folder, `-backend=false` skips remote state and `-input=false` forbids questions. The same loop does the plan and then `terraform show -json` of each environment into `build/<env>.json`.

From `Makefile`:

```make
	  $(OFFLINE) $(TF) -chdir=$$dir plan -var-file=plan-only.tfvars -out=$(CURDIR)/$(BUILD)/$$env.tfplan -input=false -lock=false -no-color | grep -E "^Plan:|Error" && \
```

The plan runs with placeholder credentials, writes the saved plan, and `grep` keeps only the summary line (`Plan: N to add, ...`) or an error. `&& \` means "only continue if this worked". The loop ends with `|| exit 1`, so a failure in either environment fails the target.

From `Makefile`:

```make
check: $(STAMP) ## policy rules on both plans, and the rules in the plan equal detections/ (make plan first)
	@for env in $(ENVS); do \
	  echo "== policy rules on $$env"; \
```

The OPA rules run on both plans ([opa-rego.md](opa-rego.md)). The last line of the target, `$(DR) audit-rules --plan $(BUILD)/workload.json`, checks that the deployed rules equal the files in `detections/`.

From `Makefile`:

```make
	@$(DR) scan --archive $(REHEARSAL) --expect D1,D2,D4 | tail -n 1
```

In `demo-drill`, `@` hides the command and `| tail -n 1` keeps only the last line of the output. `--expect D1,D2,D4` makes the scan fail if one of them does not fire. The target replays the rehearsal archive from start to finish.

From `Makefile`:

```make
respond: ## contain from the evidence; add APPLY=--apply to change anything (a dry run by default)
	scripts/08-contain.sh $(APPLY)
```

`make respond` is a dry run. `make respond APPLY=--apply` sets the variable on the command line and passes `--apply` to the script. Nothing in the account changes unless you type it.

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
