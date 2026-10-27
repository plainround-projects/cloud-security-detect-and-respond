# pip-audit

## What it is

pip-audit is a command-line tool that checks the libraries you depend on against public lists of **known vulnerabilities** (security holes that have been reported and given an identifier). This repository pins **pip-audit 2.10.1**.

## Why this repository uses it

A secure workload can still be undermined by a vulnerable library. The lock files pin exact versions, so it is possible to ask: "does any pinned version have a known hole?" CI runs this check on every push, and `make audit` runs it locally.

## Where it appears

| Path | What it does with pip-audit |
| --- | --- |
| `Makefile` | the `audit` target |
| `.github/workflows/ci.yml` | `make audit` as a step |
| `requirements-dev.lock` | the list it checks |

## How it works underneath

pip-audit reads the pinned names and versions, sends them to a vulnerability database service (PyPI's own data, by default) and prints any matches with an advisory id and the version that fixes it. It does not run or import the libraries. The check needs network access, and the answer can change tomorrow when a new hole is reported.

## Walkthrough of this repository's use

From `Makefile`:

```make
	$(VENV)/bin/pip-audit --no-deps --disable-pip -r requirements-dev.lock
```

- `-r requirements-dev.lock`: audit the packages in this file.
- `--no-deps`: do not work out dependencies again; the file already lists every one.
- `--disable-pip`: do not call pip to resolve anything (pip-audit would otherwise create a temporary environment). This is allowed because the lock is complete and hashed.

The command prints two warnings about hashing (it would like every requirement fully hashed; here it relies on the lock) and then `No known vulnerabilities found`. The exit code is non-zero when it finds something, so `make audit` and CI fail.

## Try it yourself

```bash
make audit
```

Expect `No known vulnerabilities found` at the end (needs network access).

```bash
.venv/bin/pip-audit --version
```

Expect `pip-audit 2.10.1`.

```bash
echo $?
```

Right after `make audit`, expect `0`.

## Mistakes people make

- Reading "no known vulnerabilities" as "secure". It means no reported ones, today.
- Auditing the wrong file. This repository audits the dev lock, which includes the run-time libraries.
- Ignoring a failure in CI because "it worked yesterday". New advisories appear without any code change.

## Check yourself

1. What does pip-audit compare? *Your pinned libraries and versions against a database of known vulnerabilities.*
2. What does `--disable-pip` do? *Stops pip-audit from calling pip to resolve packages.*
3. Why does the answer change over time? *New vulnerabilities are reported against old versions.*
4. What exit code means a finding? *Non-zero.*
5. Does it import your libraries? *No.*

## Further reading

- pip-audit: <https://pypi.org/project/pip-audit/> (version 2.10.1) and <https://github.com/pypa/pip-audit>
