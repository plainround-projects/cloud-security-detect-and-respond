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

This file is `pyproject.toml`. Every line of it is shown and explained below, in the order it appears in the file. The explanations of the format come first because the whole file is written in it.

**The TOML format in one paragraph.** A line of the form `key = value` stores one setting. The key is a name; the value is text in double quotes (`"x"`), a number, `true` or `false`, a **list** written in square brackets (`["a", "b"]`) or an **inline table**, a small group of settings written on one line between curly braces (`{ text = "MIT" }`). A line in square brackets on its own, such as `[project]`, is a **table header**: every `key = value` line after it, up to the next header, belongs to that table. A dot in a header means nesting, so `[tool.ruff.lint]` is the table `lint` inside `ruff` inside `tool`. Double square brackets, such as `[[tool.mypy.overrides]]`, add **one more item** to a list of tables, so the same header can appear several times and each appearance is a separate item. A line that starts with `#` is a comment: the program ignores it, and it is written for people. Blank lines are ignored. Each tool reads only its own part of the file: ruff reads `[tool.ruff...]`, mypy reads `[tool.mypy...]`, pytest reads `[tool.pytest.ini_options]`, coverage reads `[tool.coverage...]`, import-linter reads `[tool.importlinter...]`, and every tool ignores the rest.

From `pyproject.toml` (lines 1 to 3):

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"
```

`[build-system]` tells `pip` how to turn this folder into an installable package ([setuptools.md](setuptools.md)). `requires` is the list of things that must be installed *just for the build*: here `setuptools`, version 75 or newer (`>=75` means "greater than or equal to 75"). `build-backend` names the Python module (`setuptools.build_meta`) that `pip` imports and calls to do the build.

From `pyproject.toml` (lines 5 to 13):

```toml
[project]
name = "cloud-security-detect-and-respond"
version = "0.1.0"
description = "Detection and response for a cloud account: detections as code, a timeline rebuilt from the logs, and containment from the evidence."
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
authors = [{ name = "Sumit Srivastava" }]
dependencies = ["boto3>=1.35,<2"]
```

`[project]` holds the facts about the project itself, in a form that every Python tool understands.

- `name = "cloud-security-detect-and-respond"` is the name of the package as `pip` knows it (not the folder of Python code; that is `src/`).
- `version = "0.1.0"` is the project's version number. Three numbers separated by dots: major, minor, patch.
- `description` is one sentence about the project. `pip show cloud-security-detect-and-respond` prints it.
- `readme = "README.md"` names the file that is used as the long description.
- `requires-python = ">=3.12"` says the project needs Python 3.12 or newer. `pip` refuses to install it on an older Python, so a reader gets a clear message and not a confusing crash later.
- `license = { text = "MIT" }` is an inline table: the licence is given as text, the short name of the MIT licence. The full text is in the file `LICENSE`.
- `authors = [{ name = "Sumit Srivastava" }]` is a list that holds one inline table with the author's name.
- `dependencies = ["boto3>=1.35,<2"]` lists the libraries the program needs **when it runs**, each with a **version range**. A range such as `boto3>=1.35,<2` means "version 1.35 or newer, but below 2". The comma means both conditions must hold. The range protects against a future major version that could change how the library behaves. The library is [boto3](boto3.md), the Python library for calling AWS.

From `pyproject.toml` (lines 15 to 23):

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8,<10",
    "pytest-cov>=5",
    "ruff>=0.6",
    "mypy>=1.11",
    "import-linter>=2.0",
    "pip-audit>=2.7",
]
```

`[project.optional-dependencies]` defines **groups of extra libraries** that are installed only on request. This file defines one group named `dev` (short for development). It is a list of 6 entries, one library per line, each with a version range written the same way as above. Nothing here is needed to run the program; these are the tools used to test and check it. They are installed from the lock files, not from these ranges ([pip.md](pip.md), [uv.md](uv.md)); the ranges are the *input* from which [uv](uv.md) produces the exact pins.

- `"pytest>=8,<10"`: the test runner ([pytest.md](pytest.md)). The range means 8 or newer, below 10 (both must hold).
- `"pytest-cov>=5"`: the plug-in that connects pytest to the coverage meter ([coverage.md](coverage.md)). The range means 5 or newer.
- `"ruff>=0.6"`: the linter and formatter ([ruff.md](ruff.md)). The range means 0.6 or newer.
- `"mypy>=1.11"`: the type checker ([mypy.md](mypy.md)). The range means 1.11 or newer.
- `"import-linter>=2.0"`: the checker of import rules ([import-linter.md](import-linter.md)). The range means 2.0 or newer.
- `"pip-audit>=2.7"`: the scanner for known vulnerabilities in the pinned libraries ([pip-audit.md](pip-audit.md)). The range means 2.7 or newer.

From `pyproject.toml` (lines 25 to 26):

```toml
[project.scripts]
detect-respond = "detect_respond.interfaces.cli:main"
```

`[project.scripts]` makes **commands**. Each line is `command-name = "module.path:function"`. Installing the project creates a small program called `detect-respond` in the virtual environment's `bin/` folder. When you run it, it imports the module `detect_respond.interfaces.cli` and calls the function `main` in it, which reads the command line and does the work. This is how `detect-respond ...` on the command line reaches the Python code ([setuptools.md](setuptools.md)).

From `pyproject.toml` (lines 28 to 29):

```toml
[tool.setuptools.packages.find]
where = ["src"]
```

`[tool.setuptools.packages.find]` tells setuptools where to look for Python packages. `where = ["src"]` means "search the folder `src/`". A package is a folder that contains an `__init__.py` file. Keeping the code in `src/` (the **src layout**) means the tests import the *installed* package and not whatever folder happens to be in the current directory, which catches packaging mistakes early.

From `pyproject.toml` (lines 31 to 34):

```toml
[tool.ruff]
line-length = 120
target-version = "py312"
src = ["src", "tests", "scripts"]
```

`[tool.ruff]` holds the settings that apply to both of ruff's jobs, linting and formatting ([ruff.md](ruff.md)).

- `line-length = 120`: lines longer than 120 characters are reported by the linter and wrapped by the formatter.
- `target-version = "py312"`: write and check the code as for Python 3.12; ruff may suggest newer syntax that 3.12 allows.
- `src = ["src", "tests", "scripts"]`: the folders that hold this project's own code. The import-sorting rule uses this list to decide which imports are "first party" (this project) and which are third party, so it can group them correctly.

From `pyproject.toml` (lines 36 to 37):

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "N", "C4", "RUF", "PT", "S", "D100", "D101", "D103", "D104"]
```

`[tool.ruff.lint]` configures the linter. `select` is the list of **rule families** that are switched on. A code is letters, optionally followed by digits; a bare letter group selects every rule that starts with it. Here, one by one:

- `"E"`: style errors from pycodestyle, such as lines that are too long or bad whitespace.
- `"F"`: mistakes found by pyflakes, such as an import that is never used or a name that is not defined.
- `"I"`: isort rules, which require imports to be sorted and grouped in one standard order.
- `"B"`: bugbear, a set of rules for constructs that are probably bugs, such as a mutable default argument.
- `"UP"`: pyupgrade, which reports old syntax that newer Python replaced.
- `"SIM"`: simplify, which suggests shorter equivalent code.
- `"N"`: pep8-naming, which checks that classes, functions and constants are named in the standard style.
- `"C4"`: comprehension rules, which prefer a list or dict comprehension over a clumsier loop.
- `"RUF"`: rules that are specific to ruff itself.
- `"PT"`: rules for how pytest tests are written.
- `"S"`: security rules (from bandit), for example a hard-coded password or a call that runs a shell.
- `"D100"`, `"D101"`, `"D103"`, `"D104"`: docstring rules, selected one at a time. A **docstring** is the text in triple quotes at the top of a module, class or function. D100 requires one on every module, D101 on every public class, D103 on every public function and D104 on every package. (D102, for public methods, is deliberately not selected.)

From `pyproject.toml` (lines 39 to 41):

```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D", "S101", "S105", "S106", "S603", "S607"]
"scripts/**" = ["D"]
```

`[tool.ruff.lint.per-file-ignores]` switches rules **off for some paths only**. The key is a path pattern (`**` means "any depth of folders") and the value is the list of rules to skip there.

- `"tests/**" = ["D", "S101", "S105", "S106", "S603", "S607"]`: in the tests, `D` (all docstring rules) is skipped because test names already describe the behavior; `S101` is skipped because tests are *supposed* to use `assert`; `S105` and `S106` are skipped because tests contain fake passwords and tokens on purpose; `S603` and `S607` are skipped because a test may start another program (such as `make`) as a sub-process.
- `"scripts/**" = ["D"]`: the helper scripts under `scripts/` do not need docstrings.

From `pyproject.toml` (lines 43 to 48):

```toml
[tool.mypy]
python_version = "3.12"
strict = true
files = ["src", "tests", "scripts"]
explicit_package_bases = true
mypy_path = ["src"]
```

`[tool.mypy]` configures the type checker ([mypy.md](mypy.md)).

- `python_version = "3.12"`: check the code as if it runs on Python 3.12.
- `strict = true`: switch on the strictest group of checks. In mypy 2.4 this single setting turns on all of these: `disallow_any_generics` (a container such as `list` must say what it holds), `disallow_subclassing_any` (no class may inherit from something of unknown type), `disallow_untyped_calls` (a typed function may not call an untyped one), `disallow_untyped_defs` (every function needs type hints), `disallow_incomplete_defs` (no function may be half-annotated), `check_untyped_defs` (also check the inside of functions that have no hints), `disallow_untyped_decorators` (a decorator must be typed), `warn_redundant_casts` (report a cast that changes nothing), `warn_unused_ignores` (report a `# type: ignore` comment that is not needed), `warn_return_any` (report a function that returns an untyped value where a type was promised), `no_implicit_reexport` (a name imported into a module is not automatically part of that module's public names), `strict_equality` (report comparisons between types that can never be equal) and `extra_checks` (a few additional strict rules).
- `files = ["src", "tests", "scripts"]`: what to check when you run plain `mypy` with no arguments.
- `explicit_package_bases = true` and `mypy_path = ["src"]`: tell mypy that the folder `src/` is the root from which package names start, so the module `detect_respond.domain.x` is found at `src/detect_respond/domain/x.py` and is not confused with a module of the same name elsewhere.

From `pyproject.toml` (lines 50 to 52):

```toml
[[tool.mypy.overrides]]
module = ["boto3", "boto3.*", "botocore", "botocore.*"]
ignore_missing_imports = true
```

This is the first `[[tool.mypy.overrides]]` item. `module` lists the modules it applies to: `boto3` and `botocore` and everything inside them (`boto3.*`, `botocore.*`). `ignore_missing_imports = true` tells mypy not to complain that it cannot find type information for them. The AWS library ships without type hints that mypy can read, so without this line every `import boto3` would be an error. The values that come back from boto3 are treated as `Any`, which is why the code keeps them inside the infrastructure layer ([boto3.md](boto3.md)).

From `pyproject.toml` (lines 54 to 59):

```toml
# Test functions are named for the behavior they check; annotating every one adds noise, not safety.
[[tool.mypy.overrides]]
module = ["tests.*"]
disallow_untyped_defs = false
disallow_incomplete_defs = false
disallow_untyped_calls = false
```

The comment line above the header explains the next block: test functions are named for the behavior they check, and annotating every one adds noise and no safety.

`[[tool.mypy.overrides]]` adds one **override**: settings that apply only to some modules. `module = ["tests.*"]` selects every module in the `tests` package. The three settings `disallow_untyped_defs`, `disallow_incomplete_defs` and `disallow_untyped_calls` are set to `false`, which relaxes three of the strict checks listed above for the tests only. Production code stays fully strict.

From `pyproject.toml` (lines 61 to 67):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers -m 'not e2e'"
pythonpath = ["src", "."]
markers = [
    "e2e: runs the plan-and-check pipeline with Terraform installed (make test-e2e)",
]
```

`[tool.pytest.ini_options]` configures the test runner ([pytest.md](pytest.md)).

- `testpaths = ["tests"]`: when you run plain `pytest`, look for tests in the folder `tests/`.
- `addopts = "-ra --strict-markers -m 'not e2e'"`: options that are added to every run. `-r` asks for a short **summary** at the end, and the letter `a` selects "all except tests that passed", so failures, errors and skips are listed. `--strict-markers` turns a misspelled marker name into an error. `-m 'not e2e'` selects tests by **marker**: run everything except tests marked `e2e` (the slow end-to-end tests). You run those on purpose with `make test-e2e`.
- `pythonpath = ["src", "."]`: extra folders put on Python's import path. `src` lets the tests import the package without installing it first; `.` (the repository root) lets them import `tests.builders`.
- `markers`: the list of markers that are allowed. The one entry, `e2e`, has its description after the colon, so `pytest --markers` explains it.

From `pyproject.toml` (lines 69 to 71):

```toml
[tool.coverage.run]
source = ["detect_respond"]
branch = true
```

`[tool.coverage.run]` configures how coverage is **measured** ([coverage.md](coverage.md)). `source = ["detect_respond"]` limits the measurement to this project's own packages, so libraries and test files are not counted. `branch = true` also records which way each `if` and loop went, not only whether each line ran, so an `if` whose "false" side is never tested shows up.

From `pyproject.toml` (lines 73 to 75):

```toml
[tool.coverage.report]
show_missing = true
skip_covered = false
```

`[tool.coverage.report]` configures the **report**. `show_missing = true` adds a column that lists the line numbers that never ran. `skip_covered = false` keeps files that are 100 percent covered in the table, so the table lists every file.

From `pyproject.toml` (lines 77 to 79):

```toml
[tool.importlinter]
root_package = "detect_respond"
include_external_packages = true
```

`[tool.importlinter]` configures the checker of import rules ([import-linter.md](import-linter.md)). `root_package = "detect_respond"` names the package(s) whose imports are analyzed. `include_external_packages = true` also puts installed libraries (such as `boto3`) into the import graph, which a rule that forbids a library needs.

From `pyproject.toml` (lines 81 to 89):

```toml
[[tool.importlinter.contracts]]
name = "Layers: interfaces -> infrastructure -> application -> domain, never upward"
type = "layers"
layers = [
    "detect_respond.interfaces",
    "detect_respond.infrastructure",
    "detect_respond.application",
    "detect_respond.domain",
]
```

Each `[[tool.importlinter.contracts]]` header adds one **contract**, a rule. `name` is the label printed in the report. `type = "layers"` is a rule about order: `layers` lists packages from highest to lowest, and a higher layer may import a lower one but a lower layer may **never** import a higher one. Here the order is `interfaces` (the command line), `infrastructure` (files and the cloud), `application` (the use cases), `domain` (the rules). So the domain cannot import anything from the other three, and nothing may import the interfaces.

From `pyproject.toml` (lines 91 to 95):

```toml
[[tool.importlinter.contracts]]
name = "Domain and application know nothing about AWS"
type = "forbidden"
source_modules = ["detect_respond.domain", "detect_respond.application"]
forbidden_modules = ["boto3", "botocore"]
```

This contract has `type = "forbidden"`: the `source_modules` ["detect_respond.domain", "detect_respond.application"] may not import any of the `forbidden_modules` ["boto3", "botocore"], **directly or through a chain** of other modules. This keeps the rules and the use cases free of those libraries, so they can be tested without them.

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
