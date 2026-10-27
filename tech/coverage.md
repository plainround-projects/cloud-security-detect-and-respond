# coverage.py and pytest-cov

## What it is

**Test coverage** answers one question: while the tests ran, which lines of the program were executed? A line that never ran has never been checked by any test. **coverage.py** is the Python library that records this. **pytest-cov** is a plugin that connects coverage.py to pytest, so one command runs the tests and records coverage. This repository pins **coverage 7.17.0** and **pytest-cov 7.1.0**.

## Why this repository uses it

The rule for this project is that the domain logic is covered almost fully. The domain holds the decisions (is this call allowed?), so an untested branch there could hide a wrong "allowed". The `make test` command fails if the domain and application layers fall below 95 percent.

## Where it appears

| Path | What it does with coverage |
| --- | --- |
| `pyproject.toml` | `[tool.coverage.run]` and `[tool.coverage.report]` settings |
| `Makefile` | `make test` runs `pytest --cov` and then `coverage report --fail-under=95` |
| `.gitignore` | ignores the `.coverage` data file |

## How it works underneath

coverage.py asks Python to tell it every time a line runs (Python's tracing hooks). It stores the set of executed lines in a file called `.coverage` in the current folder. `coverage report` reads that file and compares it with the list of lines that exist in your source, and prints a table. **Branch coverage** also records, for each `if`, whether both outcomes (true and false) happened.

## Walkthrough of this repository's use

From `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["detect_respond"]
branch = true
```

- `source` limits measurement to the package of this repository, not to libraries.
- `branch = true` turns on branch coverage. The columns `Branch` and `BrPart` (partial branches) in the report come from it.

From `pyproject.toml`:

```toml
[tool.coverage.report]
show_missing = true
skip_covered = false
```

- `show_missing` adds a `Missing` column that lists the line numbers that never ran.
- `skip_covered = false` keeps fully covered files in the table, so the whole table is visible.

From `Makefile`:

```make
	$(PY) -m pytest tests/unit --cov --cov-report=term
	$(PY) -m coverage report --include='src/*/domain/*,src/*/application/*' --fail-under=95
```

- `--cov` (with no value) uses `source` from the settings. `--cov-report=term` prints the table in the terminal.
- The second command re-reads the same `.coverage` file, keeps only the domain and application files (`--include` with two patterns), and exits with an error code if the total is under 95. This is the gate: make stops there.

## Try it yourself

```bash
.venv/bin/pytest tests/unit --cov --cov-report=term | grep -E "cli.py|TOTAL"
```

Expect a row for `src/detect_respond/interfaces/cli.py` with about 97 percent and a `Missing` column listing lines 180 and 193, then a `TOTAL` row (about 99 percent over the whole package). The thin command-line code is the part the unit tests reach least.

```bash
.venv/bin/python -m coverage report --include='src/*/domain/*,src/*/application/*' --fail-under=95
```

Expect a `TOTAL` of 100 percent and exit code 0 (`echo $?`): the rules and the use cases are fully covered, so even `--fail-under=100` passes here. Remove the `--include=...` part and use `--fail-under=100`: the whole package is at 99 percent, so the command prints `Coverage failure: total of 99 is less than fail-under=100` and exits with 2.

```bash
.venv/bin/python -m coverage --version
```

Expect `Coverage.py, version 7.17.0 with C extension`.

## Mistakes people make

- Chasing 100 percent. Coverage says a line ran, not that its result was checked. This repository aims for near-full coverage in the domain, and relies on tests that assert behavior.
- Measuring the wrong folders and getting a flattering number. `source` names the packages, so test files are not counted.
- Forgetting that `.coverage` is a data file. It is ignored by git (`.gitignore`) and removed by `make clean`.

## Check yourself

1. What does `.coverage` contain? *The lines (and branches) that ran during the tests.*
2. What extra does `branch = true` measure? *Whether both outcomes of each condition happened.*
3. Why does `make test` run `coverage report` a second time? *To apply a threshold (`--fail-under=95`) to just the domain and application files.*
4. What does a `Missing` column show? *The line numbers no test executed.*
5. Why can 100 percent coverage still hide a bug? *A line can run without any test checking its result.*

## Further reading

- coverage.py 7.17: <https://coverage.readthedocs.io/en/7.17.0/>
- pytest-cov 7.1: <https://pytest-cov.readthedocs.io/en/v7.1.0/>
