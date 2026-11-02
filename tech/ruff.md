# ruff

## What it is

ruff is a command-line tool for Python that does two jobs very fast. As a **linter** it reads your code and reports likely mistakes and style problems (an unused import, a missing docstring, a risky call). As a **formatter** it rewrites the layout of your code to one consistent style (spaces, line breaks, quotes). This repository pins **ruff 0.17.3**.

## Why this repository uses it

A security project should not let small mistakes through, and a team should not argue about spacing. ruff runs on every `make lint` and in CI. Its security rules (the `S` family, from the "bandit" tool) flag things like hard-coded passwords and unsafe subprocess calls.

## Where it appears

| Path | What it does with ruff |
| --- | --- |
| `pyproject.toml` | `[tool.ruff]` and `[tool.ruff.lint]`: line length, Python version, which rules are on |
| `Makefile` | `make lint` runs `ruff check` and `ruff format --check`; `make fmt` fixes |
| `.ruff_cache/` | ruff's cache (ignored by git) |

## How it works underneath

ruff parses each Python file into a tree (a **syntax tree**), then runs rules over the tree. Each rule has a code: one or more letters and digits (`E501`, `S105`). A selected prefix switches on every rule that starts with it (`"E"` is all `E` rules). The formatter does not look at meaning; it prints the same tree in a fixed layout. Both are fast because ruff is written in Rust and does not run your code.

## Walkthrough of this repository's use

From `pyproject.toml`:

```toml
[tool.ruff]
line-length = 120
target-version = "py312"
src = ["src", "tests", "scripts"]
```

- `line-length`: lines longer than 120 characters are reported (`E501`) and the formatter wraps at 120.
- `target-version`: the oldest Python the code must run on; ruff will not suggest syntax newer than 3.12.
- `src`: the folders where first-party code lives, so import sorting can tell "ours" from "installed".

From `pyproject.toml`:

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "N", "C4", "RUF", "PT", "S", "D100", "D101", "D103", "D104"]
```

Each entry switches on a family of rules:

| Code | Family | Catches |
| --- | --- | --- |
| `E` | pycodestyle errors | long lines, bad spacing |
| `F` | Pyflakes | unused imports and variables, undefined names |
| `I` | isort | imports in the wrong order |
| `B` | bugbear | likely bugs, such as a mutable default argument |
| `UP` | pyupgrade | old syntax that has a newer form |
| `SIM` | simplify | code that can be written more simply |
| `N` | pep8-naming | names that break the naming style |
| `C4` | comprehensions | clumsy list or dict building |
| `RUF` | ruff-specific | for example an unused `noqa` comment |
| `PT` | pytest style | for example several conditions in one `assert` |
| `S` | bandit | security: hard-coded passwords, `subprocess`, `assert` in production code |
| `D100`..`D104` | docstrings | a missing docstring on a module, a public class, a public function, a package |

From `pyproject.toml`:

```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D", "S101", "S105", "S106", "S603", "S607"]
"scripts/**" = ["D"]
```

Rules can be relaxed for a path, never silently. Tests do not need docstrings (`D`), may use `assert` (`S101`), may contain fake passwords (`S105`, `S106`), and may start `make` as a sub-process (`S603`, `S607`). `scripts/` skips docstring rules. Nothing under `src/` is relaxed.

The Makefile commands:

From `Makefile`:

```make
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .
```

`check .` lints every file under the current folder. `format --check` reports files that the formatter would change, and exits non-zero without changing them. `make fmt` runs `ruff check --fix .` (applies safe fixes) and `ruff format .` (rewrites files).

### Every setting, one by one

The settings of ruff live in `pyproject.toml`, in tables whose names start with `tool.ruff`. A **table** in TOML is a group of `key = value` lines under a header in square brackets; `[tool.ruff]` is a table named `ruff` inside a table named `tool`, the place every tool reads its own settings from ([toml.md](toml.md)). Every key that this repository sets, in file order:

From `pyproject.toml` (line 31):

```toml
[tool.ruff]
```

The header: every line below it, up to the next header, is a setting of ruff itself.

From `pyproject.toml` (line 32):

```toml
line-length = 120
```

`line-length = 120`: the longest line, in characters, that the formatter will produce and that rule `E501` accepts. A longer line is reported by `ruff check` and rewrapped by `ruff format`. A whole number; the default is 88.

From `pyproject.toml` (line 33):

```toml
target-version = "py312"
```

`target-version = "py312"`: the oldest Python the code must run on. Ruff will not suggest or accept syntax newer than this, and its rules about old syntax (`UP`) are measured against it. `py312` means Python 3.12; the project itself requires 3.12 or newer (`requires-python`, see [setuptools.md](setuptools.md)).

From `pyproject.toml` (line 34):

```toml
src = ["src", "tests", "scripts"]
```

`src`: the folders that hold this project's own code, listed so the import sorter (`I`) can tell a first-party import (ours, sorted in its own group) from an installed library. Without it, ruff guesses from the current folder and may group a project import with the libraries.

From `pyproject.toml` (line 35):

```toml
extend-exclude = ["tech"]
```

`extend-exclude = ["tech"]`: folders ruff must not look at, **in addition to** the ones it already skips by default (such as `.venv`, `.git` and caches). `tech` is the folder of these notes. Their code blocks are short excerpts (for example the body of a class without its `class` line), which the formatter would try to rewrite and `ruff format --check` would then report as unformatted; excluding the folder keeps `make lint` green without changing a single quoted line.

From `pyproject.toml` (line 37):

```toml
[tool.ruff.lint]
```

The header of the lint table: settings that apply to `ruff check` (the checker), not to `ruff format` (the formatter).

From `pyproject.toml` (line 38):

```toml
select = ["E", "F", "I", "B", "UP", "SIM", "N", "C4", "RUF", "PT", "S", "D100", "D101", "D103", "D104"]
```

`select` is the list of rule **prefixes** that are switched on. A rule has a code made of letters and digits (`E501`); naming just the letters switches on every rule that starts with them, and naming a full code switches on that one rule. Rules not selected are not run, whatever their merit. Each entry here:

| Entry | Family | What it reports |
| --- | --- | --- |
| `E` | pycodestyle errors | Style errors from the Python style guide (PEP 8) such as `E501` a line longer than the limit, or `E711` comparing to `None` with `==`. |
| `F` | Pyflakes | Real mistakes: `F401` an import that is never used, `F841` a variable that is set and never read, `F821` a name that does not exist. |
| `I` | isort | `I001`: the import lines are not sorted and grouped in the standard order (standard library first, then installed libraries, then this project). |
| `B` | flake8-bugbear | Patterns that are probably bugs, such as `B006` a list or dictionary as a default argument value (it is shared between calls) or `B008` a function call in a default value. |
| `UP` | pyupgrade | Old-style syntax that has a newer form, such as `UP006` writing `typing.List[int]` where `list[int]` works. |
| `SIM` | flake8-simplify | Code that can be shorter, such as `SIM108` an `if`/`else` that only assigns a value and could be one conditional expression. |
| `N` | pep8-naming | Names that break the naming style: `N802` a function name that is not lower case, `N801` a class name that is not CapWords. |
| `C4` | flake8-comprehensions | Clumsy ways to build a list, set or dictionary, such as `C400` `list(x for x in y)` instead of `[x for x in y]`. |
| `RUF` | Ruff-specific rules | Checks written for ruff itself, for example `RUF100` a `# noqa` comment that no longer suppresses anything. |
| `PT` | flake8-pytest-style | Test style: `PT011` `pytest.raises` for an error type that is too broad without a `match`, `PT018` an `assert` that joins several conditions with `and`. |
| `S` | flake8-bandit | Security smells: `S101` use of `assert`, `S105` a string that looks like a hard-coded password, `S603` starting a sub-process, `S607` starting a program by a partial path, `S310` opening a URL whose scheme is not checked. |
| `D100` | pydocstyle | `D100`: a public module (a `.py` file) has no docstring. |
| `D101` | pydocstyle | `D101`: a public class has no docstring. |
| `D103` | pydocstyle | `D103`: a public function has no docstring. |
| `D104` | pydocstyle | `D104`: a public package (a folder with `__init__.py`) has no docstring. |

`D102` (a public method without a docstring) and `D105`, `D106`, `D107` (magic methods, nested classes, `__init__`) are **not** selected, which is why methods and constructors in this project do not need a docstring while modules, classes and functions do.

From `pyproject.toml` (line 40):

```toml
[tool.ruff.lint.per-file-ignores]
```

The header of the table that turns rules off for some paths only. Each key is a path pattern in quotes (`**` means "any number of folders"); each value is the list of rule prefixes not to run on files that match.

From `pyproject.toml` (line 41):

```toml
"tests/**" = ["D", "S101", "S105", "S106", "S603", "S607"]
```

For files matching `tests/**`, these are switched off:
  - every docstring rule (the letter `D` alone is the whole family). Test functions are named for the behavior they check, so a docstring on each would repeat the name.
  - `S101`, the use of `assert`. An `assert` is how a test says what must be true, so it is the point of a test file.
  - `S105`, a string that looks like a hard-coded password. Tests use made-up tokens and key ids on purpose.
  - `S106`, a hard-coded password passed as an argument. Same reason as `S105`.
  - `S603`, starting a sub-process. The end-to-end test starts `make` as a sub-process.
  - `S607`, starting a program by a partial path (`make`, not `/usr/bin/make`). The test relies on `PATH`, as a person at a terminal does.

Nothing under `src/` is relaxed: the production code meets every selected rule.

From `pyproject.toml` (line 42):

```toml
"scripts/**" = ["D"]
```

For files matching `scripts/**`, these are switched off:
  - every docstring rule (the letter `D` alone is the whole family). Test functions are named for the behavior they check, so a docstring on each would repeat the name.

Nothing under `src/` is relaxed: the production code meets every selected rule.

## Try it yourself

```bash
.venv/bin/ruff --version
```

Expect `ruff 0.17.3`.

```bash
.venv/bin/ruff check src/detect_respond/domain/events.py
```

Expect `All checks passed!`.

```bash
printf 'x = 1\ndef f(a,b): return a+b\nimport os\n' > /tmp/demo_ruff.py
.venv/bin/ruff check /tmp/demo_ruff.py --isolated --select E,F,I
```

`--isolated` ignores the repository settings. Expect `E402` (import not at the top) and `F401` (`os` imported but unused).

```bash
.venv/bin/ruff format --diff --isolated /tmp/demo_ruff.py
```

Expect a diff that adds blank lines, puts `return` on its own line and writes `def f(a, b):`.

```bash
.venv/bin/ruff rule S105
```

Prints the explanation of rule `S105`, "hardcoded-password-string".

## Mistakes people make

- Silencing a rule with `# noqa` to get green. The project rule is never to weaken a check; when a constant's name looked like a password, the constant was renamed instead.
- Running `ruff format` and `ruff check --fix` and committing without looking. Read the diff.
- Expecting the linter to find logic bugs. It finds patterns, not wrong answers; the tests do that.

## Check yourself

1. What are the two jobs of ruff? *Linting (reporting problems) and formatting (rewriting layout).*
2. What does `select = ["S"]` switch on? *All security rules from the bandit family.*
3. Why does `tests/**` ignore `S101`? *Tests use `assert` by design; in production code `assert` can be removed by Python, so it is flagged there.*
4. What does `ruff format --check` do? *Reports files that would change and exits non-zero, without changing them.*
5. Does ruff run your code? *No. It reads the code as text and trees.*

## Further reading

- ruff documentation: <https://docs.astral.sh/ruff/> (version 0.17.3)
- Rule index: <https://docs.astral.sh/ruff/rules/>
