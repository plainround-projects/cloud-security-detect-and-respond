# TOML

## What it is

TOML is a file format for settings. It is plain text, easy for a person to read, and unambiguous for a program. The file `pyproject.toml` is the single settings file of a Python project: what the project is, what it needs, and how each tool should behave. This repository follows TOML 1.0, which Python 3.11 and newer can read with the standard `tomllib` module.

## Why this repository uses it

The project rule is "one tool config file". Instead of a separate settings file for ruff, mypy, pytest, coverage and import-linter, all of them read their settings from `pyproject.toml`. A reader opens one file and sees every quality gate.

## Where it appears

| Path | What it holds |
| --- | --- |
| `pyproject.toml` | project metadata, the build system, and settings for ruff, mypy, pytest, coverage, import-linter |

(`.terraform.lock.hcl` and the `.tf` files are a different format, see [terraform.md](terraform.md).)

## How it works underneath

A TOML file is a set of **key = value** lines grouped into **tables**. A table starts with a header in square brackets. A dot in a header means nesting: `[tool.ruff.lint]` is the table `lint` inside `ruff` inside `tool`. Values can be text (`"x"`), numbers, true/false, lists (`[...]`) and inline tables (`{ text = "MIT" }`). Double brackets `[[name]]` add one more item to a list of tables. Each tool looks only at its own `[tool.<name>]` part and ignores the rest.

## Walkthrough of this repository's use

From `pyproject.toml`:

```toml
[project]
name = "cloud-security-detect-and-respond"
version = "0.1.0"
requires-python = ">=3.12"
license = { text = "MIT" }
authors = [{ name = "Sumit Srivastava" }]
dependencies = ["boto3>=1.35,<2"]
```

- `[project]` is the standard table for project metadata.
- `requires-python`: pip refuses to install on an older Python.
- `license = { text = "MIT" }` is an inline table (a table written on one line).
- `authors = [{ name = ... }]` is a list that holds one inline table.
- `dependencies`: the run-time libraries, as ranges. `boto3>=1.35,<2` means "1.35 or newer, but below 2".

From `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8,<10",
    "pytest-cov>=5",
]
```

An **optional dependency group** named `dev`. pip installs it only when asked (`uv pip compile --extra dev`). The full list has six tools; the example above is shortened.

From `pyproject.toml`:

```toml
[project.scripts]
detect-respond = "detect_respond.interfaces.cli:main"
```

A table whose keys are command names and whose values are `module:function`. See [setuptools.md](setuptools.md).

From `pyproject.toml`:

```toml
[[tool.importlinter.contracts]]
name = "Domain and application know nothing about AWS"
type = "forbidden"
source_modules = ["detect_respond.domain", "detect_respond.application"]
```

The double brackets mean this is one entry in a list of contracts; the file has two such entries, one after another. Each tool section is explained in its own file: [ruff.md](ruff.md), [mypy.md](mypy.md), [pytest.md](pytest.md), [coverage.md](coverage.md), [import-linter.md](import-linter.md).

Comments start with `#`. One appears above the `tests.*` override in the mypy settings and explains why that relaxation exists.

## Try it yourself

```bash
.venv/bin/python -c "import tomllib; d = tomllib.load(open('pyproject.toml','rb')); print(d['project']['name'], d['tool']['ruff']['line-length'])"
```

Expect `cloud-security-detect-and-respond 120`.

```bash
.venv/bin/python -c "import tomllib; d = tomllib.load(open('pyproject.toml','rb')); print(len(d['tool']['importlinter']['contracts']))"
```

Expect `2`: the double-bracket entries become a list.

```bash
.venv/bin/python -c "import tomllib; print(list(tomllib.load(open('pyproject.toml','rb'))['tool']))"
```

Expect `['setuptools', 'ruff', 'mypy', 'pytest', 'coverage', 'importlinter']`.

## Mistakes people make

- Using single brackets where a list of tables is meant (`[tool.x.contracts]` instead of `[[tool.x.contracts]]`): the second contract would replace the first or be a syntax error.
- Forgetting quotes around text values.
- Putting a setting in the wrong table; a tool silently ignores a table that is not its own.

## Check yourself

1. What does `[tool.ruff.lint]` mean? *The table `lint` nested in `ruff` nested in `tool`.*
2. What do double brackets mean? *One more item in a list of tables.*
3. Which tool reads `[tool.mypy]`? *mypy; other tools ignore it.*
4. What is `{ text = "MIT" }`? *An inline table: a small table on one line.*
5. Why keep everything in one file? *One place shows every quality gate.*

## Further reading

- TOML 1.0 specification: <https://toml.io/en/v1.0.0>
- `pyproject.toml` guide: <https://packaging.python.org/en/latest/guides/writing-pyproject-toml/>
