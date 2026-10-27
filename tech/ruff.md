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
