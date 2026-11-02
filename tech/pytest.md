# pytest

## What it is

pytest is a library and command for writing and running automated tests in Python. A **test** is a small function that runs some code and checks the result. If a check fails, the test fails, and pytest tells you which one and why. This repository pins **pytest 9.1.1** (`requirements-dev.lock`; `pyproject.toml` allows `>=8,<10`).

## Why this repository uses it

The lesson is about detecting and containing an intruder. Every claim ("detection D2 fires when a bucket is made public", "containment denies the old session") has a test that replays it on synthetic events, so a change that breaks a detection turns the build red. No test needs a cloud account.

## Where it appears

| Path | What it does with pytest |
| --- | --- |
| `pyproject.toml` | `[tool.pytest.ini_options]`: where tests are, default options, the `e2e` marker |
| `tests/unit/detect_respond/` | tests of the pattern matcher, the detections, the timeline, the drill measure, containment, the archive and the command line |
| `tests/e2e/test_pipeline.py` | the whole offline pipeline through `make` |
| `Makefile` | `make test` and `make test-e2e` call pytest |

## How it works underneath

pytest starts one Python process. It **collects** tests: it imports every file named `test_*.py` under `testpaths`, and registers each function named `test_*`. It runs each test; a plain Python `assert` that is false raises an error, which pytest reports with the values of both sides. A **fixture** is a function that prepares something a test needs (`tmp_path` gives a fresh temporary folder). A **marker** is a label on a test (`@pytest.mark.e2e` via `pytestmark`) that you can select or exclude on the command line.

## Walkthrough of this repository's use

From `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers -m 'not e2e'"
pythonpath = ["src", "."]
markers = [
    "e2e: runs the plan-and-check pipeline with Terraform installed (make test-e2e)",
]
```

- `testpaths`: where to look when you run plain `pytest`.
- `addopts`: options added to every run. `-ra` prints a short summary of every test that did not simply pass. `--strict-markers` makes an unknown marker an error, so a typo cannot silently skip a test. `-m 'not e2e'` means "run tests whose marker is not `e2e`": the slow end-to-end tests are off by default. `make test-e2e` passes `-m e2e`, and the last `-m` wins.
- `pythonpath`: extra folders put on the import path; `src` lets tests import `detect_respond`, and `.` lets them import `tests.builders`.
- `markers`: declares the `e2e` marker so `--strict-markers` accepts it.

**Parametrized tests** run one function with many inputs:

From `tests/unit/detect_respond/test_pattern_and_detections.py`:

```python
@pytest.mark.parametrize(
    ("pattern", "target", "expected"),
```

Each tuple becomes its own test case, named from the values, for example `test_the_matcher_follows_the_event_pattern_language[pattern0-target0-True]`.

**Expecting an error** uses a context manager:

From `tests/unit/detect_respond/test_drill.py`:

```python
    with pytest.raises(DrillError, match="no call"):
```

The block passes only if the code inside raises that error and its message matches the pattern.

**Fixtures from pytest itself.** `tmp_path` (a temporary folder), `capsys` (captures what the code prints) and `monkeypatch` (changes an attribute or environment variable for one test and puts it back) appear throughout `tests/unit/`.

**Fakes instead of the cloud.** `tests/unit/detect_respond/test_response.py` defines small classes (`FakeClock`, `FakeRevoker`) that have the same methods as the real clock and the real IAM adapter, so containment runs with no network. `tests/builders.py` builds audit events.

**The e2e marker.** In `tests/e2e/test_pipeline.py`, `pytestmark = pytest.mark.e2e` labels every test in the file, and the tests run `make validate` and `make demo-drill` as sub-processes.

### Every setting, one by one

pytest reads its settings from the table `[tool.pytest.ini_options]` (the name is historical: the same keys once lived in a file called `pytest.ini`). Every key that this repository sets:

From `pyproject.toml` (line 62):

```toml
[tool.pytest.ini_options]
```

The header of the pytest table.

From `pyproject.toml` (line 63):

```toml
testpaths = ["tests"]
```

`testpaths`: the folders pytest searches when you run `pytest` with no path. It looks there for files named `test_*.py` or `*_test.py` and, inside them, for functions whose names start with `test`. Here only `tests`, so it never wanders into `src`, `infra` or `.venv`.

From `pyproject.toml` (line 64):

```toml
addopts = "-ra --strict-markers -m 'not e2e'"
```

`addopts`: command-line options added in front of every run, as if you had typed them. Three are set:

- `-ra`: at the end, print a one-line summary of every test that did **not** simply pass. `-r` means "show a report summary" and the letter `a` means "all except passed", so skipped, failed, errored, expected-failure and similar outcomes are all listed.
- `--strict-markers`: a test marked with a name that is not declared in `markers` is an error, not a warning.
- `-m 'not e2e'`: run only tests whose marker expression is true. `not e2e` means "tests that do not carry the `e2e` marker", so the slow end-to-end tests are off by default. `make test-e2e` passes `-m e2e` later on the command line, and the last `-m` wins. The quotes are single because the whole value is inside TOML double quotes.

From `pyproject.toml` (line 65):

```toml
pythonpath = ["src", "."]
```

`pythonpath`: extra folders placed at the front of the list Python searches when a test file runs `import`. `src` makes `import detect_respond` work without installing the package; `.` (the repository root) makes `from tests import builders` work.

From `pyproject.toml` (lines 66 to 68):

```toml
markers = [
    "e2e: runs the plan-and-check pipeline with Terraform installed (make test-e2e)",
]
```

`markers`: the list of **marker** names the project defines. A marker is a label that a test can carry (`@pytest.mark.e2e`, or `pytestmark = pytest.mark.e2e` for a whole file) so that groups of tests can be selected or skipped with `-m`. Each entry is `name: description`; the description shows in `pytest --markers`. Because `--strict-markers` is on, a marker that is not listed here is an error, so a typo such as `@pytest.mark.e2f` cannot silently run nothing.

## Try it yourself

```bash
.venv/bin/pytest tests/unit/detect_respond/test_pattern_and_detections.py -q
```

Expect `44 passed`.

```bash
.venv/bin/pytest --collect-only -q tests/unit/detect_respond/test_pattern_and_detections.py | sed -n 1,2p
```

Expect lines such as `tests/unit/detect_respond/test_pattern_and_detections.py::test_the_matcher_follows_the_event_pattern_language[pattern0-target0-True]`: the parametrized names.

```bash
.venv/bin/pytest -k "event_pattern_language" tests/unit/detect_respond/test_pattern_and_detections.py -q
```

Expect `24 passed, 20 deselected`: `-k` selects tests by name.

```bash
.venv/bin/pytest --markers | grep e2e
```

Expect the line that `pyproject.toml` declares for `e2e`.

## Mistakes people make

- A test that cannot fail. Here the detections are also tested against events they must *not* match, and a drill with the containment call removed must report "not measured" rather than a time; both prove the checks can fail.
- Tests that depend on each other's order or on shared files. These tests use `tmp_path` and builders, so each starts clean.
- Forgetting to declare a marker. `--strict-markers` turns that into an error.
- Sleeping in tests to wait for time to pass. The code takes a clock as an argument (`contain(revoker, clock, ...)`), and the tests pass `FakeClock`, which always says the same moment.

## Check yourself

1. What does `-m 'not e2e'` in `addopts` do? *Skips the tests marked `e2e` unless you pass `-m e2e`.*
2. What does `--strict-markers` protect you from? *A misspelled marker name that would silently select nothing.*
3. What is a fixture? *A function that prepares something a test needs, such as `tmp_path`.*
4. How does a plain `assert` report a failure? *pytest rewrites it to show the values on both sides.*
5. Why are there fakes such as `FakeRevoker` in the tests? *So containment runs with no cloud account or network.*

## Further reading

- pytest 9.1 documentation: <https://docs.pytest.org/en/9.1.x/>
- Configuration options (`addopts`, `testpaths`, `markers`): <https://docs.pytest.org/en/stable/reference/reference.html#configuration-options>
