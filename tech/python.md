# Python

## What it is

Python is a programming language. You write instructions in text files that end in `.py`, and a program called the **interpreter** reads them and runs them. This repository pins **Python 3.12 or newer** (`requires-python = ">=3.12"`); it was verified with 3.13, and the CI uses 3.12.

A **type hint** is a note in the code that says what kind of value a name holds (`error_code: str | None`). Python does not enforce hints when it runs. A separate tool, `mypy` (see [mypy.md](mypy.md)), reads them and reports mismatches.

## Why this repository uses it

The lesson asks for detections written as data, a timeline rebuilt from the logs, two measured times (to detect, to contain) and a containment step. Python is the language of all of it: a matcher that decides whether an event satisfies a detection's pattern, code that reads the log archive and rebuilds what one credential did, and a small adapter that changes the account. A few helper scripts also use it.

## Where it appears

| Path | What it does with Python |
| --- | --- |
| `src/detect_respond/` | the package behind the command `detect-respond` |
| `tests/` | the tests, written in Python |
| `scripts/make_drill_fixtures.py` | writes the synthetic audit archive of the rehearsal |
| `pyproject.toml` | declares the Python version, the package and the tools ([toml.md](toml.md)) |

## How it works underneath

You run `python something.py`. The interpreter turns the text into an internal form, then runs it line by line, in one process, in memory. A **module** is one `.py` file. A **package** is a folder of modules with an `__init__.py` file. `import x` finds module `x`, runs it once and gives you its names. Python looks for modules in the folders on `sys.path`; installing this project with `pip install -e .` puts `src/` on that path (see [pip.md](pip.md)).

A **virtual environment** (`.venv/`) is a private copy of the interpreter and its installed libraries, so this project does not disturb other projects. `make install` creates it.

## Walkthrough of this repository's use

**Layers are folders.** The package has four sub-packages: `domain` (the rules: events, patterns, detections, the timeline, the drill measure, containment, the digest check, posture), `application` (the use cases), `infrastructure` (files and the one AWS adapter) and `interfaces` (the command line and the text it prints). [import-linter.md](import-linter.md) enforces that `domain` imports nothing from the others.

**Postponed type hints.** Almost every file starts with:

From `src/detect_respond/domain/events.py`:

```python
from __future__ import annotations
```

This tells Python to keep type hints as text instead of evaluating them at once. It lets a class name itself in a hint (`-> AuditEvent` inside `class AuditEvent`).

**Dataclasses.** A dataclass is a class where Python writes the boring methods for you.

From `src/detect_respond/domain/events.py`:

```python
@dataclass(frozen=True)
class AuditEvent:
    """The fields of one record that detections, timelines and drills use. `raw` keeps the whole record."""

    event_id: str
    time: datetime
    name: str
```

`@dataclass` reads the annotated names and generates `__init__`, `__repr__` and `__eq__`. `frozen=True` makes the object **immutable**: assigning to a field raises `FrozenInstanceError`. Immutable values cannot change under you, which matters for evidence. The text in triple quotes right after the class line is a **docstring**.

From `src/detect_respond/domain/events.py`:

```python
    raw: Mapping[str, Any] = field(repr=False, compare=False)
```

`field(...)` adjusts one field. `repr=False` keeps the (large) raw record out of printed output, and `compare=False` leaves it out of equality tests, so two events are equal when their parsed fields are equal.

**Dates and times.** A `datetime` is a date with a time. An **aware** one carries its timezone; a naive one does not.

From `src/detect_respond/domain/events.py`:

```python
    return datetime.fromisoformat(text.replace("Z", "+00:00"))
```

The audit log writes `2026-10-22T11:03:42Z`, where `Z` means UTC. `fromisoformat` understands `+00:00`, so the code swaps the letter for it and gets an aware datetime. Subtracting two aware datetimes gives a `timedelta`, which is how the two measured times are computed.

**Properties and named constructors.** `@property` lets a method be read like a field. `@classmethod` marks a method that belongs to the class, not to one object; `cls` is the class itself.

From `src/detect_respond/domain/events.py`:

```python
    @property
    def denied(self) -> bool:
        """True when the call failed because the caller was not allowed."""
        return self.error_code in DENIAL_CODES
```

**Recursion.** A function that calls itself handles nested data.

From `src/detect_respond/domain/pattern.py`:

```python
        elif isinstance(expected, Mapping):
            nested = event.get(key)
            if not isinstance(nested, Mapping) or not matches(expected, nested):
                return False
```

If a pattern field is itself a dictionary, the matcher looks at the same field in the event and calls `matches` again on the two inner dictionaries. `isinstance(x, Mapping)` asks "is this dictionary-like?".

**Named errors.** Each failure the tool expects has its own class, so callers can catch exactly it.

From `src/detect_respond/domain/errors.py`:

```python
class UnsupportedPatternError(DetectRespondError):
    """A detection pattern uses an operator the matcher does not implement; guessing could hide a missed alert."""
```

`class B(A)` means "B is a kind of A". The matcher raises this error for a pattern operator it does not know, instead of quietly never matching: a silent miss would mean a missed alert.

**Immutable updates.** `dataclasses.replace` makes a copy with some fields changed.

From `src/detect_respond/domain/detections.py`:

```python
        return replace(self, pattern=json.loads(text), parameters=remaining)
```

**Protocols (ports).** `typing.Protocol` describes the methods a collaborator must have, without naming a class.

From `src/detect_respond/application/ports.py`:

```python
class Clock(Protocol):
    """The current time, injected so containment is testable."""

    def now(self) -> datetime:
        """An aware datetime."""
        ...
```

The containment use case asks for "something with `now()`". In production that is the system clock; in tests it is a class that always says the same moment.

**The standard library.** Python ships with modules used throughout: `json` ([json.md](json.md)), `pathlib.Path` (file paths as objects), `argparse` (command-line options and sub-commands), `gzip` (compressed log files), `hashlib` (SHA-256 fingerprints) and `datetime`.

From `src/detect_respond/domain/digest.py`:

```python
        elif hashlib.sha256(content).hexdigest() != entry["hashValue"].lower():
```

A **hash** is a fixed-size fingerprint of some bytes; changing one byte changes the fingerprint. The digest file lists the expected fingerprint of every log file.

**Entry points.** `[project.scripts]` in `pyproject.toml` creates the `detect-respond` command from `detect_respond.interfaces.cli:main`. `src/detect_respond/__main__.py` makes `python -m detect_respond` work. `main()` returns a number, and `raise SystemExit(main())` ends the program with that **exit code** (0 means success).

## Try it yourself

Run these from the repository root after `make install`.

```bash
.venv/bin/python --version
```

Expect `Python 3.13.12` (or your 3.12/3.13 patch version).

```bash
.venv/bin/python -c "from detect_respond.domain.events import parse_time; print(parse_time('2026-10-22T11:03:42Z'))"
```

Expect `2026-10-22 11:03:42+00:00`: an aware datetime.

```bash
.venv/bin/python -c "
from detect_respond.domain.pattern import matches
print(matches({'a': [{'prefix': 'ab'}]}, {'a': 'abc'}), matches({'a': [{'prefix': 'ab'}]}, {'a': 'xab'}))"
```

Expect `True False`: the value must start with `ab`.

```bash
.venv/bin/python -c "
from datetime import timedelta
from detect_respond.domain.drill import format_duration
print(format_duration(timedelta(seconds=412)), format_duration(timedelta(seconds=32)), format_duration(None))"
```

Expect `6 min 52 s 32 s not measured`.

```bash
.venv/bin/python -c "
from detect_respond.domain.posture import Acceptance
a = Acceptance('f', 'because', '2026-10-22'); a.reason = 'x'"
```

Expect a traceback ending in `FrozenInstanceError: cannot assign to field 'reason'`.

## Mistakes people make

- Running `python` instead of `.venv/bin/python`, and then not finding the installed libraries. This repository's `Makefile` always uses `$(PY)`, the venv's interpreter.
- Mixing naive and aware datetimes. Python refuses to subtract them. Everything here is converted to aware UTC at the edge.
- Treating type hints as checks. They are checked by `mypy` (`make lint`), not by Python itself.
- Catching `Exception` everywhere. The command line catches only the package's named errors and a few built-in ones for bad input, so a real bug is not hidden.
- Using a mutable default such as `def f(x=[])`. The list is shared between calls; the code uses `field(default_factory=...)` and tuples.

## Check yourself

1. What does `frozen=True` on a dataclass do? *It makes instances immutable; assigning to a field raises `FrozenInstanceError`.*
2. What is an aware datetime? *One that carries its timezone, so two of them can be subtracted safely.*
3. Why does the matcher raise an error for an unknown operator? *A silent non-match would hide a missed alert.*
4. What does a `Protocol` like `Clock` give the use case? *A description of the methods it needs, so any matching object works, such as the system clock or a test double.*
5. What does `raise SystemExit(main())` do? *Ends the program with the exit code that `main()` returned.*

## Further reading

- Python 3.12 documentation: <https://docs.python.org/3.12/>
- Data classes: <https://docs.python.org/3.12/library/dataclasses.html>
- `datetime`: <https://docs.python.org/3.12/library/datetime.html>
- `typing.Protocol`: <https://docs.python.org/3.12/library/typing.html#typing.Protocol>
