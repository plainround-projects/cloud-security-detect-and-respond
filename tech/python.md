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

Every Python file of the project is shown below, in the order of its layers, and every line is explained. Read this primer first; the same ideas appear everywhere.

**Running Python.** The **interpreter** is the program `python`. It reads a `.py` text file from top to bottom and carries out each statement. A **module** is one `.py` file; a **package** is a folder of modules with an `__init__.py` file. `import x` finds the module `x`, runs it once and makes its names available. A **virtual environment** (`.venv/`) is a private folder with its own interpreter and libraries, so this project does not disturb other projects.

**Names and values.** `name = value` gives a name to a value. Values are text (`"abc"`), numbers, `True`/`False`/`None` (nothing), **lists** `[a, b]` (ordered, changeable), **tuples** `(a, b)` (ordered, fixed), **sets** `{a, b}` (no order, no repeats) and **dictionaries** `{key: value}` (a lookup table). Indentation (four spaces) is the structure: lines indented under a header belong to it.

**Functions.** `def name(a, b):` defines a **function**, a named group of statements; `return x` hands a value back. Parameters can have **type hints** (`a: int`) and defaults (`b=3`). A hint is a note for people and for the type checker ([mypy.md](mypy.md)); Python does not enforce it. `*` in a parameter list means "everything after me must be given by name". `*args` collects extra positional values, `**kwargs` collects extra named ones. A **lambda** is a function written in one line: `lambda x: x + 1`. A function defined inside another can use the outer one's variables; this is called a **closure**.

**Classes.** A **class** is a blueprint for objects that bundle data with functions (**methods**). `self` is the object a method works on. A **dataclass** (`@dataclass`) is a class where Python writes the constructor, the comparison and the printout from the list of fields; `frozen=True` makes instances unchangeable. A **decorator** (a line starting with `@`) wraps the function or class under it. `@property` makes a method readable like a field. `@classmethod` and `@staticmethod` belong to the class, not to one object. An **Enum** is a fixed list of named values. A **Protocol** describes the methods a collaborator must have, without naming a class.

**Control flow.** `if/elif/else` chooses a branch; `for x in things:` repeats for each item; `while` repeats while a condition holds; `try/except` catches an **exception** (an error that stops the program unless it is caught); `raise Name(...)` throws one; `with open(...) as f:` opens something and closes it when the block ends. A **comprehension** builds a list, set or dictionary in one expression: `[f(x) for x in things if cond]`. A **generator expression** in `any(...)`, `all(...)` or `sum(...)` produces values one at a time. An **f-string** (`f"text {value}"`) pastes values into text. `is` tests that two names are the very same object; `==` tests equal value.

**Tests.** A function whose name starts with `test_` is run by `pytest` ([pytest.md](pytest.md)); a plain `assert condition` fails the test if the condition is false.

### The package `src/detect_respond/`

Four layers as folders: `domain` (the rules, no input or output), `application` (the use cases), `infrastructure` (files and the one cloud adapter) and `interfaces` (the command line) ([import-linter.md](import-linter.md)).

#### `src/detect_respond/domain/errors.py`

From `src/detect_respond/domain/errors.py` (line 1):

```python
"""Named errors of the detection and response tooling."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/domain/errors.py` (lines 4 to 5):

```python
class DetectRespondError(Exception):
    """Base class: every error this package raises on purpose."""
```

The base class of every error this package raises on purpose. `class X(Exception):` means "a kind of `Exception`", Python's built-in error type. The body is only a docstring; the class exists as one name that the command line can catch to tell a deliberate error from a bug.

From `src/detect_respond/domain/errors.py` (lines 8 to 9):

```python
class UnsupportedPatternError(DetectRespondError):
    """A detection pattern uses an operator the matcher does not implement; guessing could hide a missed alert."""
```

A kind of `DetectRespondError`, raised when a detection pattern uses an operator the matcher does not implement. Refusing is deliberate: guessing could hide a missed alert.

From `src/detect_respond/domain/errors.py` (lines 12 to 13):

```python
class InvalidDetectionError(DetectRespondError):
    """A detection file is missing a field or has the wrong shape."""
```

Raised when a detection file lacks a field or has the wrong shape.

From `src/detect_respond/domain/errors.py` (lines 16 to 17):

```python
class InvalidLogError(DetectRespondError):
    """A log or digest file cannot be read as the audit trail's format."""
```

Raised when a log or digest file cannot be read as the audit trail's format.

From `src/detect_respond/domain/errors.py` (lines 20 to 21):

```python
class DrillError(DetectRespondError):
    """The events do not contain what the drill measurement needs."""
```

Raised when the events do not contain what the drill measurement needs.

From `src/detect_respond/domain/errors.py` (lines 24 to 25):

```python
class PlanError(DetectRespondError):
    """The Terraform plan does not contain what the rule audit needs."""
```

Raised when the Terraform plan does not contain what the rule audit needs.

#### `src/detect_respond/domain/events.py`

From `src/detect_respond/domain/events.py` (line 1):

```python
"""An audit-log event, parsed once from a CloudTrail record."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/domain/events.py` (lines 3 to 11):

```python
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from detect_respond.domain.errors import InvalidLogError
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `import json`: makes the standard-library module `json` (reads and writes JSON text) available; its contents are used as `json.name`.
- `from collections.abc import Mapping`: brings `Mapping` (the type "dictionary-like, read only") from the standard-library module `collections.abc` (abstract types for collections, used in type hints) into this file, so it can be used without the module prefix.
- `from dataclasses import dataclass, field`: brings `dataclass` (the decorator that turns a class of fields into a class with a ready-made constructor, comparison and printout), `field` (the function that adjusts one field of a dataclass) from the standard-library module `dataclasses` (the dataclass helpers) into this file, so it can be used without the module prefix.
- `from datetime import datetime`: brings `datetime` from the standard-library module `datetime` (dates and times) into this file, so it can be used without the module prefix.
- `from typing import Any`: brings `Any` (the type "anything", used where the shape is not known) from the standard-library module `typing` (names used in type hints) into this file, so it can be used without the module prefix.
- `from detect_respond.domain.errors import InvalidLogError`: brings `InvalidLogError` from another module of this project into this file, so it can be used without the module prefix.

From `src/detect_respond/domain/events.py` (line 13):

```python
DENIAL_CODES = ("AccessDenied", "AccessDeniedException", "Client.UnauthorizedOperation", "UnauthorizedOperation")
```

A constant: the tuple of `errorCode` values that mean "the caller was not allowed".

From `src/detect_respond/domain/events.py` (lines 16 to 18):

```python
def parse_time(text: str) -> datetime:
    """Parse the `2026-10-22T11:03:42Z` timestamps of the audit log into aware datetimes."""
    return datetime.fromisoformat(text.replace("Z", "+00:00"))
```

Parses the timestamps of the audit log, such as `2026-10-22T11:03:42Z`, into **aware** datetimes (ones that carry a timezone). `text.replace("Z", "+00:00")` swaps the letter `Z` (UTC) for the numeric form that `datetime.fromisoformat` understands.

From `src/detect_respond/domain/events.py` (lines 21 to 37):

```python
@dataclass(frozen=True)
class AuditEvent:
    """The fields of one record that detections, timelines and drills use. `raw` keeps the whole record."""

    event_id: str
    time: datetime
    name: str
    source: str
    region: str
    principal_arn: str
    access_key_id: str
    source_ip: str
    user_agent: str
    error_code: str | None
    request: Mapping[str, Any]
    raw: Mapping[str, Any] = field(repr=False, compare=False)

```

A frozen dataclass: one audit record, parsed once. `@dataclass(frozen=True)` writes the constructor and makes instances unchangeable. Each `name: type` line is a field: `time` is a `datetime`, `error_code: str | None` is text or nothing, `request: Mapping[str, Any]` is a read-only dictionary of any values. The last field, `raw: Mapping[str, Any] = field(repr=False, compare=False)`, keeps the whole original record; `repr=False` leaves it out of printed output and `compare=False` leaves it out of equality tests.

From `src/detect_respond/domain/events.py` (lines 38 to 60):

```python
    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> AuditEvent:
        """Build an event from a CloudTrail record, or from a `lookup-events` entry that wraps one."""
        if "CloudTrailEvent" in record:
            record = json.loads(record["CloudTrailEvent"])
        try:
            identity = record.get("userIdentity") or {}
            return cls(
                event_id=record["eventID"],
                time=parse_time(record["eventTime"]),
                name=record["eventName"],
                source=record["eventSource"],
                region=record.get("awsRegion", ""),
                principal_arn=identity.get("arn", ""),
                access_key_id=identity.get("accessKeyId", ""),
                source_ip=record.get("sourceIPAddress", ""),
                user_agent=record.get("userAgent", ""),
                error_code=record.get("errorCode"),
                request=record.get("requestParameters") or {},
                raw=record,
            )
        except KeyError as error:
            raise InvalidLogError(f"a record lacks the field {error}") from error
```

A class method (`@classmethod`; `cls` is the class) that builds an event from a raw record, or from a `lookup-events` entry that wraps one.

- `if "CloudTrailEvent" in record: record = json.loads(record["CloudTrailEvent"])` unwraps the JSON text that `lookup-events` adds around each record ([json.md](json.md)).
- The `try:` block builds the event: `identity = record.get("userIdentity") or {}` reads the caller (an empty dictionary if missing); `record["eventID"]`, `record["eventName"]` and `record["eventSource"]` must exist; `record.get("awsRegion", "")` has a default; `parse_time(record["eventTime"])` converts the time; `record.get("requestParameters") or {}` gives an empty dictionary when missing.
- `except KeyError as error: raise InvalidLogError(f"a record lacks the field {error}") from error` turns a missing required key into a clear error, keeping the original as the cause.

From `src/detect_respond/domain/events.py` (lines 62 to 65):

```python
    @property
    def denied(self) -> bool:
        """True when the call failed because the caller was not allowed."""
        return self.error_code in DENIAL_CODES
```

A property (read as `event.denied`): true when `error_code` is one of `DENIAL_CODES`.

From `src/detect_respond/domain/events.py` (lines 67 to 70):

```python
    @property
    def service(self) -> str:
        """The service prefix, for example `iam` for `iam.amazonaws.com`."""
        return self.source.split(".")[0]
```

A property: the service prefix, for example `iam` for `iam.amazonaws.com`: `self.source.split(".")[0]` cuts the text at the dots and takes the first piece.

From `src/detect_respond/domain/events.py` (lines 72 to 80):

```python
    def envelope(self) -> dict[str, Any]:
        """The event as EventBridge delivers it to a rule, which is what detection patterns match against."""
        return {
            "source": f"aws.{self.service}",
            "detail-type": "AWS API Call via CloudTrail",
            "region": self.region,
            "time": self.raw["eventTime"],
            "detail": dict(self.raw),
        }
```

The event as EventBridge delivers it to a rule, which is the shape detection patterns are written against ([aws-eventbridge.md](aws-eventbridge.md)): a dictionary with `source` (`aws.<service>`), `detail-type`, `region`, `time` and `detail` (a copy of the raw record: `dict(self.raw)`).

From `src/detect_respond/domain/events.py` (lines 82 to 87):

```python
    def session_of(self, role_name: str) -> str | None:
        """The session name when this event was made by a session of the role, otherwise None."""
        marker = f":assumed-role/{role_name}/"
        if marker in self.principal_arn:
            return self.principal_arn.split(marker, 1)[1]
        return None
```

Returns the session name when the event was made by a session of the role, otherwise `None`. `marker = f":assumed-role/{role_name}/"` is the text that appears in the caller's ARN for a role session; `self.principal_arn.split(marker, 1)[1]` cuts the ARN at the marker (once) and keeps the part after it ([aws-sts.md](aws-sts.md)).

#### `src/detect_respond/domain/pattern.py`

From `src/detect_respond/domain/pattern.py` (lines 1 to 2):

```python
"""The EventBridge event-pattern language, as far as the detections use it: exact values, `anything-but`, `prefix`,
`suffix`, `exists`, nested objects and `$or`. Anything else raises instead of silently never matching."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/domain/pattern.py` (lines 4 to 9):

```python
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from detect_respond.domain.errors import UnsupportedPatternError
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `from collections.abc import Mapping`: brings `Mapping` (the type "dictionary-like, read only") from the standard-library module `collections.abc` (abstract types for collections, used in type hints) into this file, so it can be used without the module prefix.
- `from typing import Any`: brings `Any` (the type "anything", used where the shape is not known) from the standard-library module `typing` (names used in type hints) into this file, so it can be used without the module prefix.
- `from detect_respond.domain.errors import UnsupportedPatternError`: brings `UnsupportedPatternError` from another module of this project into this file, so it can be used without the module prefix.

From `src/detect_respond/domain/pattern.py` (line 11):

```python
_OPERATORS = {"anything-but", "prefix", "suffix", "exists"}
```

A set of the four pattern operators the matcher implements besides exact values: `anything-but`, `prefix`, `suffix`, `exists`.

From `src/detect_respond/domain/pattern.py` (lines 14 to 26):

```python
def matches(pattern: Mapping[str, Any], event: Mapping[str, Any]) -> bool:
    """True when the event satisfies every field of the pattern (and, if present, one branch of each `$or`)."""
    for key, expected in pattern.items():
        if key == "$or":
            if not any(matches(branch, event) for branch in expected):
                return False
        elif isinstance(expected, Mapping):
            nested = event.get(key)
            if not isinstance(nested, Mapping) or not matches(expected, nested):
                return False
        elif not _leaf_matches(expected, event.get(key), key in event):
            return False
    return True
```

True when the event satisfies every field of the pattern. It is **recursive** (it calls itself for nested data).

- `for key, expected in pattern.items():` looks at each field of the pattern.
- `if key == "$or":` the special key `$or` holds a list of alternative sub-patterns; `if not any(matches(branch, event) for branch in expected): return False` requires that at least one branch matches.
- `elif isinstance(expected, Mapping):` a field whose pattern is a dictionary needs the event's field to be a dictionary too: `nested = event.get(key)`; `if not isinstance(nested, Mapping) or not matches(expected, nested): return False` descends one level.
- `elif not _leaf_matches(expected, event.get(key), key in event): return False` handles a plain field: the pattern value is a list of alternatives, and `key in event` tells whether the event has the field at all.
- If no check failed, `return True`.

From `src/detect_respond/domain/pattern.py` (lines 29 to 31):

```python
def _leaf_matches(alternatives: list[Any], value: Any, present: bool) -> bool:
    values = value if isinstance(value, list) else [value]
    return any(_alternative_matches(alternative, values, present) for alternative in alternatives)
```

A leaf field: `values = value if isinstance(value, list) else [value]` treats the event's value as a list (an event field may itself be a list), and `any(_alternative_matches(alternative, values, present) for alternative in alternatives)` is true if one alternative matches.

From `src/detect_respond/domain/pattern.py` (lines 34 to 50):

```python
def _alternative_matches(alternative: Any, values: list[Any], present: bool) -> bool:
    if not isinstance(alternative, Mapping):
        return present and alternative in values
    unknown = set(alternative) - _OPERATORS
    if unknown or len(alternative) != 1:
        raise UnsupportedPatternError(f"pattern operator {sorted(alternative)} is not implemented")
    operator, argument = next(iter(alternative.items()))
    if operator == "exists":
        return present == bool(argument)
    if not present:
        return False
    if operator == "anything-but":
        excluded = argument if isinstance(argument, list) else [argument]
        return all(item not in excluded for item in values)
    if operator == "prefix":
        return any(isinstance(item, str) and item.startswith(argument) for item in values)
    return any(isinstance(item, str) and item.endswith(argument) for item in values)
```

Does one alternative match?

- `if not isinstance(alternative, Mapping): return present and alternative in values` an exact value matches when the field exists and the value is among the event's.
- Otherwise the alternative is an operator object such as `{"prefix": "ab"}`. `unknown = set(alternative) - _OPERATORS` finds unknown operator names; `if unknown or len(alternative) != 1: raise UnsupportedPatternError(...)` refuses rather than guessing.
- `operator, argument = next(iter(alternative.items()))` takes the one (name, argument) pair.
- `exists`: the field must be present (or absent) as asked. If the field is missing, no other operator can match.
- `anything-but`: `all(item not in excluded for item in values)`; `prefix` and `suffix`: some text value starts or ends with the argument (`str.startswith`, `str.endswith`).

#### `src/detect_respond/domain/detections.py`

From `src/detect_respond/domain/detections.py` (line 1):

```python
"""A detection is a rule written as data: an event pattern, a severity and the responder's first step."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/domain/detections.py` (lines 3 to 12):

```python
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from detect_respond.domain.errors import InvalidDetectionError
from detect_respond.domain.events import AuditEvent
from detect_respond.domain.pattern import matches
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `import json`: makes the standard-library module `json` (reads and writes JSON text) available; its contents are used as `json.name`.
- `from collections.abc import Mapping`: brings `Mapping` (the type "dictionary-like, read only") from the standard-library module `collections.abc` (abstract types for collections, used in type hints) into this file, so it can be used without the module prefix.
- `from dataclasses import dataclass, field, replace`: brings `dataclass` (the decorator that turns a class of fields into a class with a ready-made constructor, comparison and printout), `field` (the function that adjusts one field of a dataclass), `replace` (the function that makes a copy of a dataclass instance with some fields changed) from the standard-library module `dataclasses` (the dataclass helpers) into this file, so it can be used without the module prefix.
- `from typing import Any`: brings `Any` (the type "anything", used where the shape is not known) from the standard-library module `typing` (names used in type hints) into this file, so it can be used without the module prefix.
- `from detect_respond.domain.errors import InvalidDetectionError`: brings `InvalidDetectionError` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.events import AuditEvent`: brings `AuditEvent` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.pattern import matches`: brings `matches` from another module of this project into this file, so it can be used without the module prefix.

From `src/detect_respond/domain/detections.py` (line 14):

```python
SEVERITIES = ("low", "medium", "high", "critical")
```

The four allowed severity words, as a tuple.

From `src/detect_respond/domain/detections.py` (line 15):

```python
DEPLOY_TARGETS = {"global", "home", "watch"}
```

A set of the three places a rule may be deployed to: `global`, `home` and `watch`.

From `src/detect_respond/domain/detections.py` (lines 18 to 34):

```python
@dataclass(frozen=True)
class Detection:
    """One detection. `deploy_to` names where the rule runs: `global` (the Region that receives global service events),
    `home` (the Region the account works in) and `watch` (each Region the account does not operate in)."""

    detection_id: str
    title: str
    severity: str
    description: str
    first_step: str
    prevention: str
    deploy_to: tuple[str, ...]
    pattern: Mapping[str, Any]
    parameters: tuple[str, ...] = ()
    parameter_variables: Mapping[str, str] = field(default_factory=dict)
    include_read_only: bool = False

```

A frozen dataclass: a rule written as data. Fields: id, title, severity, description, the responder's first step, a prevention, where it is deployed (`deploy_to`), the event `pattern`, the `parameters` (placeholders still to be filled, default none), `parameter_variables` (which Terraform variable fills which placeholder) and `include_read_only` (whether it needs read-only calls too). The docstring explains the three places.

From `src/detect_respond/domain/detections.py` (lines 35 to 59):

```python
    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> Detection:
        """Validate and build from the JSON form."""
        try:
            detection = cls(
                detection_id=raw["id"],
                title=raw["title"],
                severity=raw["severity"],
                description=raw["description"],
                first_step=raw["firstStep"],
                prevention=raw["prevention"],
                deploy_to=tuple(raw["deployTo"]),
                pattern=raw["pattern"],
                parameters=tuple(raw.get("parameters", ())),
                parameter_variables=raw.get("parameterVariables", {}),
                include_read_only=bool(raw.get("includeReadOnly", False)),
            )
        except KeyError as error:
            raise InvalidDetectionError(f"detection lacks the field {error}") from error
        if detection.severity not in SEVERITIES:
            raise InvalidDetectionError(f"{detection.detection_id}: severity must be one of {SEVERITIES}")
        unknown = set(detection.deploy_to) - DEPLOY_TARGETS
        if unknown or not detection.deploy_to:
            raise InvalidDetectionError(f"{detection.detection_id}: deployTo must name {sorted(DEPLOY_TARGETS)}")
        return detection
```

Validates and builds a detection from the decoded JSON ([json.md](json.md)).

- The `try:` block builds the object with `raw["id"]`, `raw["title"]`, ... (required keys) and `raw.get("parameters", ())` (optional ones); `tuple(raw["deployTo"])` freezes the list.
- `except KeyError as error: raise InvalidDetectionError(f"detection lacks the field {error}") from error` names a missing field.
- `if detection.severity not in SEVERITIES:` refuses an unknown severity; `unknown = set(detection.deploy_to) - DEPLOY_TARGETS` and `if unknown or not detection.deploy_to:` refuse an unknown or empty place list.
- It returns the detection.

From `src/detect_respond/domain/detections.py` (lines 61 to 67):

```python
    def with_parameters(self, values: Mapping[str, str]) -> Detection:
        """The detection with its placeholders replaced, for example the honeytoken's access key id."""
        text = json.dumps(self.pattern)
        for placeholder, value in values.items():
            text = text.replace(placeholder, value)
        remaining = tuple(p for p in self.parameters if p not in values)
        return replace(self, pattern=json.loads(text), parameters=remaining)
```

Fills the placeholders, for example the honeytoken's key id. `text = json.dumps(self.pattern)` turns the pattern into text; the loop replaces each placeholder by its value; `remaining` is the parameters that were not given; `replace(self, pattern=json.loads(text), parameters=remaining)` returns a copy of the detection with the new pattern (`replace` is the dataclass copy helper).

From `src/detect_respond/domain/detections.py` (lines 69 to 72):

```python
    @property
    def complete(self) -> bool:
        """False while a placeholder is unresolved; such a detection never fires."""
        return not self.parameters
```

A property: false while a placeholder is unresolved. Such a detection never fires.

From `src/detect_respond/domain/detections.py` (lines 74 to 76):

```python
    def fires(self, event: AuditEvent) -> bool:
        """True when the event matches the pattern. Failed calls match too: an attempt is as telling as a success."""
        return self.complete and matches(self.pattern, event.envelope())
```

True when the event matches the pattern: `self.complete and matches(self.pattern, event.envelope())`. The docstring notes that failed calls match too: an attempt is as telling as a success.

#### `src/detect_respond/domain/alerts.py`

From `src/detect_respond/domain/alerts.py` (line 1):

```python
"""The text of an alert, built from the detection and the event."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/domain/alerts.py` (lines 3 to 8):

```python
from __future__ import annotations

import json

from detect_respond.domain.detections import Detection
from detect_respond.domain.events import AuditEvent
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `import json`: makes the standard-library module `json` (reads and writes JSON text) available; its contents are used as `json.name`.
- `from detect_respond.domain.detections import Detection`: brings `Detection` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.events import AuditEvent`: brings `AuditEvent` from another module of this project into this file, so it can be used without the module prefix.

From `src/detect_respond/domain/alerts.py` (lines 11 to 34):

```python
def render_alert(template: str, detection: Detection, event: AuditEvent) -> str:
    """Fill the template the way the rule's input transformer does: `{name}` fields from the detection when the rule is
    deployed, `<name>` fields from the event when it fires."""
    text = (
        template.replace("{id}", detection.detection_id)
        .replace("{title}", detection.title)
        .replace("{severity}", detection.severity)
        .replace("{first_step}", detection.first_step)
    )
    params = json.dumps(event.request, sort_keys=True, separators=(",", ":")) if event.request else "-"
    fields = {
        "time": str(event.raw["eventTime"]),
        "who": event.principal_arn or "-",
        "source": event.source,
        "name": event.name,
        "params": params,
        "ip": event.source_ip,
        "agent": event.user_agent,
        "region": event.region,
        "event_id": event.event_id,
    }
    for name, value in fields.items():
        text = text.replace(f"<{name}>", value)
    return text
```

Fills the alert template the way the deployed rule does. `{name}` fields come from the detection when the rule is deployed; `<name>` fields come from the event when it fires.

- `text = (template.replace("{id}", ...).replace("{title}", ...)...)` is a chain of `replace` calls on the text (each returns a new text).
- `params = json.dumps(event.request, sort_keys=True, separators=(",", ":")) if event.request else "-"` shows the request parameters as compact JSON with sorted keys, or a dash.
- `fields` is a dictionary from field name to value (`event.principal_arn or "-"` shows a dash for an empty value).
- `for name, value in fields.items(): text = text.replace(f"<{name}>", value)` fills each `<name>`.
- It returns the finished alert text.

#### `src/detect_respond/domain/timeline.py`

From `src/detect_respond/domain/timeline.py` (line 1):

```python
"""Rebuild what a credential did from the audit log alone: the attacker's calls (denied too) and the responder's."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/domain/timeline.py` (lines 3 to 9):

```python
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from detect_respond.domain.detections import Detection
from detect_respond.domain.events import AuditEvent
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `from collections.abc import Iterable`: brings `Iterable` (the type "anything you can loop over") from the standard-library module `collections.abc` (abstract types for collections, used in type hints) into this file, so it can be used without the module prefix.
- `from dataclasses import dataclass`: brings `dataclass` (the decorator that turns a class of fields into a class with a ready-made constructor, comparison and printout) from the standard-library module `dataclasses` (the dataclass helpers) into this file, so it can be used without the module prefix.
- `from detect_respond.domain.detections import Detection`: brings `Detection` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.events import AuditEvent`: brings `AuditEvent` from another module of this project into this file, so it can be used without the module prefix.

From `src/detect_respond/domain/timeline.py` (line 11):

```python
CONTAINMENT_CALLS = frozenset({"PutRolePolicy", "UpdateAccessKey", "DeleteAccessKey", "DeleteRolePolicy"})
```

A `frozenset` of the four call names that count as the responder's containment calls.

From `src/detect_respond/domain/timeline.py` (lines 14 to 20):

```python
@dataclass(frozen=True)
class TimelineEntry:
    """One line of the timeline: the event, who made it, and the detections it raises."""

    event: AuditEvent
    actor: str
    detections: tuple[str, ...]
```

A frozen dataclass: one line of the timeline: the event, who made it (`attacker` or `responder`) and the detections it raises.

From `src/detect_respond/domain/timeline.py` (lines 23 to 27):

```python
def _is_attacker(event: AuditEvent, role_name: str, session: str) -> bool:
    if event.session_of(role_name) == session:
        return True
    assumed = event.name == "AssumeRole" and str(event.request.get("roleArn", "")).endswith(f":role/{role_name}")
    return assumed and event.request.get("roleSessionName") == session
```

True when the event belongs to the attacker's session: either it was made by a session of the role with that session name (`event.session_of(role_name) == session`), or it is the `AssumeRole` call that started the session. `assumed = event.name == "AssumeRole" and str(event.request.get("roleArn", "")).endswith(f":role/{role_name}")` checks the call and the role it asked for; the last line also requires the requested session name.

From `src/detect_respond/domain/timeline.py` (lines 30 to 33):

```python
def _is_responder(event: AuditEvent, role_name: str, user_name: str) -> bool:
    if event.name not in CONTAINMENT_CALLS:
        return False
    return event.request.get("roleName") == role_name or event.request.get("userName") == user_name
```

True when the event is one of the containment calls and it concerns this role or this user: `event.request.get("roleName") == role_name or event.request.get("userName") == user_name`.

From `src/detect_respond/domain/timeline.py` (lines 36 to 54):

```python
def build_timeline(
    events: Iterable[AuditEvent],
    detections: Iterable[Detection],
    role_name: str,
    session: str,
    user_name: str,
) -> tuple[TimelineEntry, ...]:
    """The session's calls and the responder's containment calls, oldest first, each with the detections it raises."""
    rules = tuple(detections)
    entries = []
    for event in sorted(events, key=lambda candidate: candidate.time):
        if _is_attacker(event, role_name, session):
            actor = "attacker"
        elif _is_responder(event, role_name, user_name):
            actor = "responder"
        else:
            continue
        entries.append(TimelineEntry(event, actor, tuple(rule.detection_id for rule in rules if rule.fires(event))))
    return tuple(entries)
```

Rebuilds what a credential did from the audit log alone.

- `rules = tuple(detections)` freezes the rules once (the parameter may be a one-shot iterable).
- `for event in sorted(events, key=lambda candidate: candidate.time):` walks the events oldest first (`key=` names the value to sort by, given as a one-line function).
- The `if/elif/else` classifies each event: attacker, responder, or `continue` (skip, it is unrelated).
- `entries.append(TimelineEntry(event, actor, tuple(rule.detection_id for rule in rules if rule.fires(event))))` records the event with the ids of the detections that fire on it.

#### `src/detect_respond/domain/drill.py`

From `src/detect_respond/domain/drill.py` (line 1):

```python
"""The two numbers the lesson asks for: time to detect and time to contain, measured from the first attacker action."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/domain/drill.py` (lines 3 to 10):

```python
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

from detect_respond.domain.errors import DrillError
from detect_respond.domain.timeline import TimelineEntry
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `from collections.abc import Mapping`: brings `Mapping` (the type "dictionary-like, read only") from the standard-library module `collections.abc` (abstract types for collections, used in type hints) into this file, so it can be used without the module prefix.
- `from dataclasses import dataclass`: brings `dataclass` (the decorator that turns a class of fields into a class with a ready-made constructor, comparison and printout) from the standard-library module `dataclasses` (the dataclass helpers) into this file, so it can be used without the module prefix.
- `from datetime import datetime, timedelta`: brings `datetime`, `timedelta` from the standard-library module `datetime` (dates and times) into this file, so it can be used without the module prefix.
- `from detect_respond.domain.errors import DrillError`: brings `DrillError` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.timeline import TimelineEntry`: brings `TimelineEntry` from another module of this project into this file, so it can be used without the module prefix.

From `src/detect_respond/domain/drill.py` (lines 13 to 22):

```python
@dataclass(frozen=True)
class DrillMeasure:
    """Measured times. `contained_at` is the first call refused after the revocation (None if none was tried)."""

    first_action: datetime
    first_alert: datetime | None
    revoked_at: datetime | None
    contained_at: datetime | None
    detections: tuple[str, ...]

```

A frozen dataclass: the measured moments: when the attacker's first action happened, when the first alert came (or `None`), when the revocation happened, when the first call was refused after it, and which detections fired.

From `src/detect_respond/domain/drill.py` (lines 23 to 26):

```python
    @property
    def time_to_detect(self) -> timedelta | None:
        """First attacker action to the first alert."""
        return None if self.first_alert is None else self.first_alert - self.first_action
```

A property: first attacker action to the first alert, a `timedelta` (the difference of two datetimes), or `None` when there was no alert.

From `src/detect_respond/domain/drill.py` (lines 28 to 31):

```python
    @property
    def time_to_contain(self) -> timedelta | None:
        """First attacker action to the first call that revocation refused."""
        return None if self.contained_at is None else self.contained_at - self.first_action
```

A property: first attacker action to the first call that the revocation refused, or `None`.

From `src/detect_respond/domain/drill.py` (lines 34 to 40):

```python
def format_duration(span: timedelta | None) -> str:
    """Seconds under a minute, otherwise minutes and seconds: `32 s`, `6 min 52 s`."""
    if span is None:
        return "not measured"
    total = int(span.total_seconds())
    minutes, seconds = divmod(total, 60)
    return f"{seconds} s" if minutes == 0 else f"{minutes} min {seconds} s"
```

Writes a duration for people. `None` becomes `not measured`. `total = int(span.total_seconds())` is whole seconds; `minutes, seconds = divmod(total, 60)` splits them into minutes and the remainder; under a minute it returns `32 s`, otherwise `6 min 52 s`.

From `src/detect_respond/domain/drill.py` (lines 43 to 61):

```python
def measure(timeline: tuple[TimelineEntry, ...], alert_times: Mapping[str, datetime]) -> DrillMeasure:
    """Measure the drill. `alert_times` maps an event id to when its alert reached the responder; an event without an
    entry is taken to alert at the moment it happened, which is the lower bound."""
    attacker = [entry for entry in timeline if entry.actor == "attacker"]
    if not attacker:
        raise DrillError("the events contain no call by the attacker's session")
    first_action = attacker[0].event.time
    alerts = [alert_times.get(e.event.event_id, e.event.time) for e in attacker if e.detections]
    revocations = [entry for entry in timeline if entry.actor == "responder" and entry.event.name == "PutRolePolicy"]
    revoked_at = revocations[0].event.time if revocations else None
    refused = [
        entry.event.time
        for entry in attacker
        if revoked_at is not None and entry.event.time > revoked_at and entry.event.denied
    ]
    fired = tuple(dict.fromkeys(rule for entry in attacker for rule in entry.detections))
    return DrillMeasure(
        first_action, min(alerts) if alerts else None, revoked_at, min(refused) if refused else None, fired
    )
```

Measures the drill from the rebuilt timeline. `alert_times` maps an event id to when its alert reached the responder; an event without an entry is taken to alert at the moment it happened, which is the lower bound.

- `attacker = [entry for entry in timeline if entry.actor == "attacker"]`; `if not attacker: raise DrillError(...)` needs at least one attacker call.
- `first_action = attacker[0].event.time`.
- `alerts = [alert_times.get(e.event.event_id, e.event.time) for e in attacker if e.detections]` collects, for each attacker call that raised a detection, the time the alert arrived.
- `revocations` are the responder's `PutRolePolicy` calls; `revoked_at` is the first one's time or `None`.
- `refused` lists the times of attacker calls that came after the revocation and were denied.
- `fired = tuple(dict.fromkeys(rule for entry in attacker for rule in entry.detections))` lists the detection ids that fired, without repeats and in order (`dict.fromkeys` keeps the first appearance of each key).
- It returns a `DrillMeasure` with `min(alerts)` (the earliest alert) and `min(refused)` (the earliest refusal), each `None` when the list is empty.

#### `src/detect_respond/domain/containment.py`

From `src/detect_respond/domain/containment.py` (line 1):

```python
"""Containment: stop a role's sessions, not only the key. Revoking the key leaves sessions already issued alive."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/domain/containment.py` (lines 3 to 8):

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `import json`: makes the standard-library module `json` (reads and writes JSON text) available; its contents are used as `json.name`.
- `from dataclasses import dataclass`: brings `dataclass` (the decorator that turns a class of fields into a class with a ready-made constructor, comparison and printout) from the standard-library module `dataclasses` (the dataclass helpers) into this file, so it can be used without the module prefix.
- `from datetime import UTC, datetime`: brings `UTC`, `datetime` from the standard-library module `datetime` (dates and times) into this file, so it can be used without the module prefix.
- `from typing import Any`: brings `Any` (the type "anything", used where the shape is not known) from the standard-library module `typing` (names used in type hints) into this file, so it can be used without the module prefix.

From `src/detect_respond/domain/containment.py` (line 10):

```python
POLICY_NAME = "deny-all-before-now"
```

A constant: the name of the inline policy that containment attaches. Using the same name each time makes a second run replace the policy.

From `src/detect_respond/domain/containment.py` (lines 13 to 28):

```python
def deny_sessions_before(moment: datetime) -> dict[str, Any]:
    """An inline policy that denies every call made with credentials issued before `moment`. New sessions, issued after
    the moment, are unaffected, so the role can be used again once the cause is fixed."""
    stamp = moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DenySessionsIssuedBeforeContainment",
                "Effect": "Deny",
                "Action": "*",
                "Resource": "*",
                "Condition": {"DateLessThan": {"aws:TokenIssueTime": stamp}},
            }
        ],
    }
```

Builds the containment policy as a dictionary: it denies every call made with credentials issued **before** a moment ([aws-iam.md](aws-iam.md)).

- `stamp = moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")` converts the moment to UTC and writes it in the form IAM expects (`strftime` formats a time with codes: `%Y` year, `%m` month, `%d` day, `%H:%M:%S` time).
- The returned dictionary has one statement: `Effect: Deny`, `Action: "*"`, `Resource: "*"` and the condition `DateLessThan` on `aws:TokenIssueTime`. New sessions, issued after the moment, are unaffected.

From `src/detect_respond/domain/containment.py` (lines 31 to 40):

```python
@dataclass(frozen=True)
class RevocationPlan:
    """What containment will do, so it can be shown before it is done."""

    role_name: str
    user_name: str
    policy_name: str
    policy: dict[str, Any]
    access_key_ids: tuple[str, ...]

```

A frozen dataclass: what containment will do, so it can be shown before it is done: the role, the user, the policy name, the policy and the user's key ids.

From `src/detect_respond/domain/containment.py` (lines 41 to 51):

```python
    def cli_commands(self) -> list[str]:
        """The same actions as AWS CLI commands, for a responder who prefers to run them by hand."""
        commands = [
            f"aws iam put-role-policy --role-name {self.role_name} --policy-name {self.policy_name} "
            f"--policy-document '{json.dumps(self.policy, separators=(',', ':'))}'"
        ]
        commands += [
            f"aws iam update-access-key --user-name {self.user_name} --access-key-id {key} --status Inactive"
            for key in self.access_key_ids
        ]
        return commands
```

The same actions as AWS CLI commands, as a list of text, for a responder who prefers to run them by hand. The first is `aws iam put-role-policy ... --policy-document '<compact JSON>'` (`json.dumps(..., separators=(',', ':'))` writes JSON without spaces); the `+=` adds, for each key, `aws iam update-access-key ... --status Inactive` ([aws-cli.md](aws-cli.md)).

From `src/detect_respond/domain/containment.py` (lines 54 to 56):

```python
def plan_revocation(role_name: str, user_name: str, access_key_ids: tuple[str, ...], now: datetime) -> RevocationPlan:
    """Plan the revocation of one role's sessions and one user's keys as of `now`."""
    return RevocationPlan(role_name, user_name, POLICY_NAME, deny_sessions_before(now), access_key_ids)
```

Plans the revocation of one role's sessions and one user's keys as of `now`: returns a `RevocationPlan` with the policy built by `deny_sessions_before(now)`.

#### `src/detect_respond/domain/digest.py`

From `src/detect_respond/domain/digest.py` (line 1):

```python
"""Tamper evidence for the archive: the digest files list a SHA-256 hash for every log file."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/domain/digest.py` (lines 3 to 8):

```python
from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `import hashlib`: makes the standard-library module `hashlib` (computes fingerprints such as SHA-256) available; its contents are used as `hashlib.name`.
- `from collections.abc import Callable, Mapping`: brings `Callable` (the type "something that can be called like a function"), `Mapping` (the type "dictionary-like, read only") from the standard-library module `collections.abc` (abstract types for collections, used in type hints) into this file, so it can be used without the module prefix.
- `from dataclasses import dataclass`: brings `dataclass` (the decorator that turns a class of fields into a class with a ready-made constructor, comparison and printout) from the standard-library module `dataclasses` (the dataclass helpers) into this file, so it can be used without the module prefix.
- `from typing import Any`: brings `Any` (the type "anything", used where the shape is not known) from the standard-library module `typing` (names used in type hints) into this file, so it can be used without the module prefix.

From `src/detect_respond/domain/digest.py` (lines 11 to 18):

```python
@dataclass(frozen=True)
class DigestResult:
    """How many logged files matched their digest, and which did not."""

    checked: int
    mismatched: tuple[str, ...]
    missing: tuple[str, ...]

```

A frozen dataclass: how many logged files were checked and which did not match (`mismatched`) or were not found (`missing`).

From `src/detect_respond/domain/digest.py` (lines 19 to 22):

```python
    @property
    def intact(self) -> bool:
        """True when every file listed in the digest is present and unchanged."""
        return not self.mismatched and not self.missing
```

A property: true when nothing mismatched and nothing is missing: `not self.mismatched and not self.missing` (an empty tuple counts as false, so `not` of it is true).

From `src/detect_respond/domain/digest.py` (lines 25 to 39):

```python
def verify_digest(digest: Mapping[str, Any], read_content: Callable[[str], bytes | None]) -> DigestResult:
    """Compare each listed file's hash with the file's uncompressed content.

    This checks the hashes only. The digest's own signature is checked by `aws cloudtrail validate-logs`, which is what
    `scripts/` runs against the real archive.
    """
    mismatched, missing = [], []
    entries = digest.get("logFiles", [])
    for entry in entries:
        content = read_content(entry["s3Object"])
        if content is None:
            missing.append(entry["s3Object"])
        elif hashlib.sha256(content).hexdigest() != entry["hashValue"].lower():
            mismatched.append(entry["s3Object"])
    return DigestResult(len(entries), tuple(mismatched), tuple(missing))
```

Compares each listed file's fingerprint with the file's uncompressed content ([aws-cloudtrail.md](aws-cloudtrail.md)). The docstring is honest about the limit: it checks the fingerprints only, and `aws cloudtrail validate-logs` checks the digest's signature.

- `mismatched, missing = [], []` starts two empty lists; `entries = digest.get("logFiles", [])`.
- For each entry: `content = read_content(entry["s3Object"])` asks for the file's bytes (`read_content` is a function passed in); `None` means the archive lacks it, so the name goes to `missing`; otherwise `hashlib.sha256(content).hexdigest() != entry["hashValue"].lower()` computes the SHA-256 fingerprint as hexadecimal text and compares it, and a difference goes to `mismatched`.
- It returns `DigestResult(len(entries), tuple(mismatched), tuple(missing))`.

#### `src/detect_respond/domain/posture.py`

From `src/detect_respond/domain/posture.py` (line 1):

```python
"""Posture findings: the baseline by severity, and the accepted risks with a reason."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/domain/posture.py` (lines 3 to 7):

```python
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `from collections.abc import Iterable, Mapping`: brings `Iterable` (the type "anything you can loop over"), `Mapping` (the type "dictionary-like, read only") from the standard-library module `collections.abc` (abstract types for collections, used in type hints) into this file, so it can be used without the module prefix.
- `from dataclasses import dataclass`: brings `dataclass` (the decorator that turns a class of fields into a class with a ready-made constructor, comparison and printout) from the standard-library module `dataclasses` (the dataclass helpers) into this file, so it can be used without the module prefix.
- `from typing import Any`: brings `Any` (the type "anything", used where the shape is not known) from the standard-library module `typing` (names used in type hints) into this file, so it can be used without the module prefix.

From `src/detect_respond/domain/posture.py` (line 9):

```python
SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
```

The four severity words in report order, as a tuple.

From `src/detect_respond/domain/posture.py` (lines 12 to 20):

```python
@dataclass(frozen=True)
class Finding:
    """One failed control, from the posture service's finding format."""

    finding_id: str
    title: str
    severity: str
    resource: str

```

A frozen dataclass: one failed control, reduced to its id, title, severity and the resource it concerns.

From `src/detect_respond/domain/posture.py` (lines 21 to 29):

```python
    @classmethod
    def from_asff(cls, raw: Mapping[str, Any]) -> Finding | None:
        """Parse a finding; None when it is not an open failure (passed, suppressed or resolved)."""
        if raw.get("Compliance", {}).get("Status") != "FAILED":
            return None
        if raw.get("Workflow", {}).get("Status") in {"SUPPRESSED", "RESOLVED"}:
            return None
        resources = raw.get("Resources") or [{}]
        return cls(raw["Id"], raw["Title"], raw["Severity"]["Label"], resources[0].get("Id", ""))
```

Parses a finding in the posture service's format (ASFF; [aws-security-hub.md](aws-security-hub.md)); returns `None` when it is not an open failure.

- `if raw.get("Compliance", {}).get("Status") != "FAILED": return None` drops findings that passed. `raw.get("Compliance", {})` gives an empty dictionary when the key is missing, so `.get("Status")` still works.
- `if raw.get("Workflow", {}).get("Status") in {"SUPPRESSED", "RESOLVED"}: return None` drops those a person already dealt with.
- `resources = raw.get("Resources") or [{}]` and `cls(raw["Id"], raw["Title"], raw["Severity"]["Label"], resources[0].get("Id", ""))` build the finding from the first resource.

From `src/detect_respond/domain/posture.py` (lines 32 to 38):

```python
@dataclass(frozen=True)
class Acceptance:
    """A finding the owner has decided to live with, and why."""

    finding_id: str
    reason: str
    accepted_on: str
```

A frozen dataclass: a finding the owner has decided to live with: its id, the reason and the date.

From `src/detect_respond/domain/posture.py` (lines 41 to 50):

```python
@dataclass(frozen=True)
class Baseline:
    """Open findings by severity at the start, after fixing, and how many of the rest are accepted with a reason."""

    start: Mapping[str, int]
    after_fixing: Mapping[str, int]
    accepted: Mapping[str, int]
    unaccepted_critical: tuple[str, ...]
    reasonless: tuple[str, ...]

```

A frozen dataclass: open findings by severity at the start, after fixing, and how many of the rest are accepted with a reason; plus `unaccepted_critical` (critical ids still open) and `reasonless` (acceptances without a reason).

From `src/detect_respond/domain/posture.py` (lines 51 to 54):

```python
    @property
    def meets_done_when(self) -> bool:
        """Every critical finding is resolved or accepted with a reason, and every acceptance has a reason."""
        return not self.unaccepted_critical and not self.reasonless
```

A property: the lesson's "done when": no unaccepted critical finding and no acceptance without a reason.

From `src/detect_respond/domain/posture.py` (lines 57 to 61):

```python
def _count(findings: Iterable[Finding]) -> dict[str, int]:
    counts = dict.fromkeys(SEVERITIES, 0)
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return counts
```

Counts findings by severity. `counts = dict.fromkeys(SEVERITIES, 0)` makes a dictionary with every severity set to 0; the loop adds one for each finding (`counts.get(finding.severity, 0) + 1` also copes with an unknown severity).

From `src/detect_respond/domain/posture.py` (lines 64 to 73):

```python
def baseline(start: Iterable[Finding], after: Iterable[Finding], acceptances: Iterable[Acceptance]) -> Baseline:
    """Compare the findings before and after fixing. An accepted finding counts as accepted, not as open."""
    starting, remaining = list(start), list(after)
    accepted_ids = {a.finding_id: a for a in acceptances}
    reasoned = {fid for fid, a in accepted_ids.items() if a.reason.strip()}
    open_after = [f for f in remaining if f.finding_id not in reasoned]
    accepted = [f for f in remaining if f.finding_id in reasoned]
    critical = tuple(f.finding_id for f in open_after if f.severity == "CRITICAL")
    reasonless = tuple(sorted(fid for fid, a in accepted_ids.items() if not a.reason.strip()))
    return Baseline(_count(starting), _count(open_after), _count(accepted), critical, reasonless)
```

Compares the findings before and after fixing. An accepted finding counts as accepted, not as open.

- `starting, remaining = list(start), list(after)` makes lists (the arguments may be one-shot iterables).
- `accepted_ids = {a.finding_id: a for a in acceptances}` is a dictionary comprehension; `reasoned` is the set of ids whose reason is not blank (`a.reason.strip()` removes spaces, so a reason of spaces counts as none).
- `open_after` are the remaining findings that are not accepted with a reason; `accepted` are the ones that are.
- `critical` lists open critical ids; `reasonless` lists acceptances with no reason, sorted.
- It returns `Baseline(...)` with the counts.

#### `src/detect_respond/application/ports.py`

From `src/detect_respond/application/ports.py` (line 1):

```python
"""What the use cases need from the outside."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/application/ports.py` (lines 3 to 11):

```python
from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any, Protocol

from detect_respond.domain.detections import Detection
from detect_respond.domain.events import AuditEvent
from detect_respond.domain.posture import Acceptance, Finding
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `from collections.abc import Iterable, Mapping`: brings `Iterable` (the type "anything you can loop over"), `Mapping` (the type "dictionary-like, read only") from the standard-library module `collections.abc` (abstract types for collections, used in type hints) into this file, so it can be used without the module prefix.
- `from datetime import datetime`: brings `datetime` from the standard-library module `datetime` (dates and times) into this file, so it can be used without the module prefix.
- `from typing import Any, Protocol`: brings `Any` (the type "anything", used where the shape is not known), `Protocol` (the base class for describing the methods a collaborator must have, without naming a class) from the standard-library module `typing` (names used in type hints) into this file, so it can be used without the module prefix.
- `from detect_respond.domain.detections import Detection`: brings `Detection` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.events import AuditEvent`: brings `AuditEvent` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.posture import Acceptance, Finding`: brings `Acceptance`, `Finding` from another module of this project into this file, so it can be used without the module prefix.

From `src/detect_respond/application/ports.py` (lines 14 to 16):

```python
class LogArchive(Protocol):
    """The central log store, read back from files synced out of the archive bucket."""

```

A **Protocol** (a description of the methods a collaborator must have, with no code) for "the central log store, read back from files". Any object with these three methods fits.

From `src/detect_respond/application/ports.py` (lines 17 to 19):

```python
    def events(self) -> Iterable[AuditEvent]:
        """Every event in the archive."""
        ...
```

Every event in the archive (`Iterable[AuditEvent]`: anything you can loop over). The body `...` means "no code here, only the shape".

From `src/detect_respond/application/ports.py` (lines 21 to 23):

```python
    def digests(self) -> Iterable[Mapping[str, Any]]:
        """Every digest file in the archive."""
        ...
```

Every digest file of the archive, as dictionaries.

From `src/detect_respond/application/ports.py` (lines 25 to 27):

```python
    def read_log(self, s3_object: str) -> bytes | None:
        """The uncompressed content of a log file, or None when the archive does not have it."""
        ...
```

The uncompressed content of a log file named as a digest names it, or `None` when the archive does not have it.

From `src/detect_respond/application/ports.py` (lines 30 to 32):

```python
class DetectionCatalog(Protocol):
    """The detections and the alert template, kept as files."""

```

A Protocol for "the detections and the alert template, kept as files".

From `src/detect_respond/application/ports.py` (lines 33 to 35):

```python
    def detections(self) -> tuple[Detection, ...]:
        """All detections."""
        ...
```

All detections, as a tuple.

From `src/detect_respond/application/ports.py` (lines 37 to 39):

```python
    def template(self) -> str:
        """The alert text template."""
        ...
```

The alert text template.

From `src/detect_respond/application/ports.py` (lines 42 to 44):

```python
class Revoker(Protocol):
    """Changes access in the account. The only port that writes."""

```

A Protocol for "changes access in the account". The docstring says it is the **only port that writes**: everything else only reads.

From `src/detect_respond/application/ports.py` (lines 45 to 47):

```python
    def list_access_keys(self, user_name: str) -> tuple[str, ...]:
        """The ids of the user's access keys."""
        ...
```

The ids of the user's access keys.

From `src/detect_respond/application/ports.py` (lines 49 to 51):

```python
    def put_role_policy(self, role_name: str, policy_name: str, policy: Mapping[str, Any]) -> None:
        """Attach an inline policy to the role."""
        ...
```

Attach an inline policy to the role.

From `src/detect_respond/application/ports.py` (lines 53 to 55):

```python
    def deactivate_access_key(self, user_name: str, access_key_id: str) -> None:
        """Make the key unusable without deleting it."""
        ...
```

Make a key unusable without deleting it.

From `src/detect_respond/application/ports.py` (lines 58 to 60):

```python
class Clock(Protocol):
    """The current time, injected so containment is testable."""

```

A Protocol for "the current time, injected so containment is testable".

From `src/detect_respond/application/ports.py` (lines 61 to 63):

```python
    def now(self) -> datetime:
        """An aware datetime."""
        ...
```

An aware datetime.

From `src/detect_respond/application/ports.py` (lines 66 to 68):

```python
class PostureSource(Protocol):
    """Findings and accepted risks from files."""

```

A Protocol for "findings and accepted risks from files".

From `src/detect_respond/application/ports.py` (lines 69 to 71):

```python
    def findings(self, name: str) -> tuple[Finding, ...]:
        """Open findings from the named file."""
        ...
```

Open findings from the named file.

From `src/detect_respond/application/ports.py` (lines 73 to 75):

```python
    def acceptances(self) -> tuple[Acceptance, ...]:
        """The accepted risks."""
        ...
```

The accepted risks.

#### `src/detect_respond/application/use_cases.py`

From `src/detect_respond/application/use_cases.py` (line 1):

```python
"""The lesson's use cases: detect, rebuild the timeline, measure, contain, verify the archive, baseline the posture."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/application/use_cases.py` (lines 3 to 17):

```python
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from detect_respond.application.ports import Clock, DetectionCatalog, LogArchive, PostureSource, Revoker
from detect_respond.domain.alerts import render_alert
from detect_respond.domain.containment import RevocationPlan, plan_revocation
from detect_respond.domain.detections import Detection
from detect_respond.domain.digest import DigestResult, verify_digest
from detect_respond.domain.drill import DrillMeasure, measure
from detect_respond.domain.events import AuditEvent
from detect_respond.domain.posture import Baseline, baseline
from detect_respond.domain.timeline import TimelineEntry, build_timeline
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `from collections.abc import Mapping`: brings `Mapping` (the type "dictionary-like, read only") from the standard-library module `collections.abc` (abstract types for collections, used in type hints) into this file, so it can be used without the module prefix.
- `from dataclasses import dataclass`: brings `dataclass` (the decorator that turns a class of fields into a class with a ready-made constructor, comparison and printout) from the standard-library module `dataclasses` (the dataclass helpers) into this file, so it can be used without the module prefix.
- `from datetime import datetime`: brings `datetime` from the standard-library module `datetime` (dates and times) into this file, so it can be used without the module prefix.
- `from detect_respond.application.ports import Clock, DetectionCatalog, LogArchive, PostureSource, Revoker`: brings `Clock`, `DetectionCatalog`, `LogArchive`, `PostureSource`, `Revoker` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.alerts import render_alert`: brings `render_alert` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.containment import RevocationPlan, plan_revocation`: brings `RevocationPlan`, `plan_revocation` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.detections import Detection`: brings `Detection` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.digest import DigestResult, verify_digest`: brings `DigestResult`, `verify_digest` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.drill import DrillMeasure, measure`: brings `DrillMeasure`, `measure` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.events import AuditEvent`: brings `AuditEvent` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.posture import Baseline, baseline`: brings `Baseline`, `baseline` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.timeline import TimelineEntry, build_timeline`: brings `TimelineEntry`, `build_timeline` from another module of this project into this file, so it can be used without the module prefix.

From `src/detect_respond/application/use_cases.py` (lines 20 to 26):

```python
@dataclass(frozen=True)
class Alert:
    """A detection that fired on an event, with the text the responder would receive."""

    detection: Detection
    event: AuditEvent
    text: str
```

A frozen dataclass: a detection that fired on an event, with the text the responder would receive.

From `src/detect_respond/application/use_cases.py` (lines 29 to 33):

```python
def resolved_detections(catalog: DetectionCatalog, parameters: Mapping[str, str]) -> tuple[Detection, ...]:
    """The catalog's detections with their placeholders filled in where a value is given."""
    return tuple(
        d.with_parameters({k: v for k, v in parameters.items() if k in d.parameters}) for d in catalog.detections()
    )
```

The catalog's detections with their placeholders filled in where a value is given: `d.with_parameters({k: v for k, v in parameters.items() if k in d.parameters})` passes only the values the detection asks for (a dictionary comprehension with a filter).

From `src/detect_respond/application/use_cases.py` (lines 36 to 46):

```python
def scan_logs(archive: LogArchive, catalog: DetectionCatalog, parameters: Mapping[str, str]) -> tuple[Alert, ...]:
    """Run every detection over every event in the archive, oldest event first.

    This is the batch twin of the rules in the account, and it also sees what a rule in one Region cannot: all Regions.
    """
    template = catalog.template()
    rules = resolved_detections(catalog, parameters)
    alerts = []
    for event in sorted(archive.events(), key=lambda candidate: candidate.time):
        alerts += [Alert(rule, event, render_alert(template, rule, event)) for rule in rules if rule.fires(event)]
    return tuple(alerts)
```

Runs every detection over every event in the archive, oldest first. The docstring notes this is the batch twin of the rules in the account, and it also sees what a rule in one Region cannot: all Regions.

- `template = catalog.template()`, `rules = resolved_detections(catalog, parameters)`.
- `for event in sorted(archive.events(), key=lambda candidate: candidate.time):` walks the events in time order.
- `alerts += [Alert(rule, event, render_alert(template, rule, event)) for rule in rules if rule.fires(event)]` adds an alert for each rule that fires on the event.
- `return tuple(alerts)`.

From `src/detect_respond/application/use_cases.py` (lines 49 to 54):

```python
@dataclass(frozen=True)
class Drill:
    """The rebuilt timeline and the measured times."""

    timeline: tuple[TimelineEntry, ...]
    measured: DrillMeasure
```

A frozen dataclass: the rebuilt timeline and the measured times.

From `src/detect_respond/application/use_cases.py` (lines 57 to 68):

```python
def run_drill(
    archive: LogArchive,
    catalog: DetectionCatalog,
    role_name: str,
    session: str,
    user_name: str,
    alert_times: Mapping[str, datetime],
) -> Drill:
    """Rebuild what the session did from the archive alone, then measure time to detect and time to contain."""
    rules = resolved_detections(catalog, {})
    timeline = build_timeline(archive.events(), rules, role_name, session, user_name)
    return Drill(timeline, measure(timeline, alert_times))
```

Rebuilds what the session did from the archive alone, then measures time to detect and time to contain: `rules = resolved_detections(catalog, {})` (no placeholders filled), `timeline = build_timeline(archive.events(), rules, role_name, session, user_name)`, then `Drill(timeline, measure(timeline, alert_times))`.

From `src/detect_respond/application/use_cases.py` (lines 71 to 76):

```python
@dataclass(frozen=True)
class Containment:
    """What containment decided and whether it was applied."""

    plan: RevocationPlan
    applied: bool
```

A frozen dataclass: what containment decided and whether it was applied.

From `src/detect_respond/application/use_cases.py` (lines 79 to 95):

```python
def contain(
    revoker: Revoker,
    clock: Clock,
    role_name: str,
    user_name: str,
    access_key_ids: tuple[str, ...],
    *,
    apply: bool,
) -> Containment:
    """Revoke the role's sessions issued before now and deactivate the user's keys. Without `apply`, only plan."""
    keys = access_key_ids or revoker.list_access_keys(user_name)
    plan = plan_revocation(role_name, user_name, keys, clock.now())
    if apply:
        revoker.put_role_policy(role_name, plan.policy_name, plan.policy)
        for key in plan.access_key_ids:
            revoker.deactivate_access_key(user_name, key)
    return Containment(plan, apply)
```

Revokes the role's sessions issued before now and deactivates the user's keys. Without `apply`, it only plans. The `*` in the parameter list makes `apply` keyword-only, so it must be written `apply=True`.

- `keys = access_key_ids or revoker.list_access_keys(user_name)` uses the ids given, or asks for the user's keys when none were given.
- `plan = plan_revocation(role_name, user_name, keys, clock.now())`.
- `if apply:` attaches the policy (`revoker.put_role_policy(...)`) and deactivates each key (`for key in plan.access_key_ids: revoker.deactivate_access_key(...)`).
- `return Containment(plan, apply)`.

From `src/detect_respond/application/use_cases.py` (lines 98 to 100):

```python
def verify_archive(archive: LogArchive) -> tuple[DigestResult, ...]:
    """Check every digest in the archive against the log files it lists."""
    return tuple(verify_digest(digest, archive.read_log) for digest in archive.digests())
```

Checks every digest in the archive against the log files it lists: `tuple(verify_digest(digest, archive.read_log) for digest in archive.digests())` (the second argument passes the method `read_log` itself as the function that reads a file).

From `src/detect_respond/application/use_cases.py` (lines 103 to 105):

```python
def posture_baseline(source: PostureSource, before: str, after: str) -> Baseline:
    """The baseline from two findings files and the accepted risks."""
    return baseline(source.findings(before), source.findings(after), source.acceptances())
```

The baseline from two findings files and the accepted risks: `baseline(source.findings(before), source.findings(after), source.acceptances())`.

#### `src/detect_respond/infrastructure/log_archive.py`

From `src/detect_respond/infrastructure/log_archive.py` (line 1):

```python
"""The central log archive, read from a folder synced out of the archive bucket (plain or gzip JSON)."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/infrastructure/log_archive.py` (lines 3 to 12):

```python
from __future__ import annotations

import gzip
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from detect_respond.domain.errors import InvalidLogError
from detect_respond.domain.events import AuditEvent
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `import gzip`: makes the standard-library module `gzip` (reads and writes gzip-compressed files) available; its contents are used as `gzip.name`.
- `import json`: makes the standard-library module `json` (reads and writes JSON text) available; its contents are used as `json.name`.
- `from collections.abc import Iterable, Mapping`: brings `Iterable` (the type "anything you can loop over"), `Mapping` (the type "dictionary-like, read only") from the standard-library module `collections.abc` (abstract types for collections, used in type hints) into this file, so it can be used without the module prefix.
- `from pathlib import Path`: brings `Path` (the class that represents a file or folder path as an object) from the standard-library module `pathlib` (file paths as objects) into this file, so it can be used without the module prefix.
- `from typing import Any`: brings `Any` (the type "anything", used where the shape is not known) from the standard-library module `typing` (names used in type hints) into this file, so it can be used without the module prefix.
- `from detect_respond.domain.errors import InvalidLogError`: brings `InvalidLogError` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.events import AuditEvent`: brings `AuditEvent` from another module of this project into this file, so it can be used without the module prefix.

From `src/detect_respond/infrastructure/log_archive.py` (line 14):

```python
DIGEST_FOLDER = "CloudTrail-Digest"
```

A constant: the folder name under which the real bucket keeps digest files.

From `src/detect_respond/infrastructure/log_archive.py` (lines 17 to 23):

```python
def _load(path: Path) -> Any:
    opener = gzip.open if path.suffix == ".gz" else open
    try:
        with opener(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise InvalidLogError(f"{path} cannot be read as a JSON log file: {error}") from error
```

Reads one JSON file, plain or gzip: `opener = gzip.open if path.suffix == ".gz" else open` chooses how to open; `with opener(path, "rt", encoding="utf-8") as handle:` opens it for reading as text and closes it after; `json.load(handle)` parses it. `except (OSError, json.JSONDecodeError) as error: raise InvalidLogError(...) from error` turns an unreadable or invalid file into a clear error.

From `src/detect_respond/infrastructure/log_archive.py` (lines 26 to 28):

```python
class DirectoryArchive:
    """A `LogArchive` over a folder. Digest files live under a `CloudTrail-Digest` folder, as in the real bucket."""

```

A class over a folder synced out of the archive bucket. It satisfies the `LogArchive` protocol.

From `src/detect_respond/infrastructure/log_archive.py` (lines 29 to 30):

```python
    def __init__(self, root: Path) -> None:
        self._root = root
```

The constructor: stores the root folder.

From `src/detect_respond/infrastructure/log_archive.py` (lines 32 to 34):

```python
    def _files(self, *, digests: bool) -> list[Path]:
        found = sorted(p for p in self._root.rglob("*") if p.is_file() and p.suffix in {".json", ".gz"})
        return [p for p in found if (DIGEST_FOLDER in p.parts) == digests]
```

Lists the JSON files under the root, either the logs or the digests. `found` is every file ending in `.json` or `.gz`, sorted (`rglob("*")` walks all sub-folders); the return keeps those for which `(DIGEST_FOLDER in p.parts) == digests`: a file is a digest if the folder name is in its path parts. The `*` makes `digests` keyword-only.

From `src/detect_respond/infrastructure/log_archive.py` (lines 36 to 42):

```python
    def events(self) -> Iterable[AuditEvent]:
        """Every record of every log file, in file order."""
        records: list[Mapping[str, Any]] = []
        for path in self._files(digests=False):
            decoded = _load(path)
            records += decoded if isinstance(decoded, list) else decoded.get("Records") or decoded.get("Events") or []
        return [AuditEvent.from_record(record) for record in records]
```

Every record of every log file, in file order: for each file, `decoded = _load(path)`, and `records += decoded if isinstance(decoded, list) else decoded.get("Records") or decoded.get("Events") or []` adds the records of whichever of the three formats it is. `[AuditEvent.from_record(record) for record in records]` parses them.

From `src/detect_respond/infrastructure/log_archive.py` (lines 44 to 46):

```python
    def digests(self) -> Iterable[Mapping[str, Any]]:
        """Every digest file."""
        return [_load(path) for path in self._files(digests=True)]
```

Every digest file, parsed: `[_load(path) for path in self._files(digests=True)]`.

From `src/detect_respond/infrastructure/log_archive.py` (lines 48 to 53):

```python
    def read_log(self, s3_object: str) -> bytes | None:
        """The uncompressed bytes of a log file named as the digest names it (a key relative to the archive root)."""
        path = self._root / s3_object
        if not path.is_file():
            return None
        return gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
```

The uncompressed bytes of a log file named as the digest names it (a key relative to the archive root). `path = self._root / s3_object` joins the path; `if not path.is_file(): return None`; `gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()` returns the uncompressed content, because the digest's fingerprint is of the uncompressed bytes.

#### `src/detect_respond/infrastructure/files.py`

From `src/detect_respond/infrastructure/files.py` (line 1):

```python
"""Detections, the alert template, posture findings and accepted risks, read from files."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/infrastructure/files.py` (lines 3 to 11):

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from detect_respond.domain.detections import Detection
from detect_respond.domain.errors import InvalidDetectionError
from detect_respond.domain.posture import Acceptance, Finding
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `import json`: makes the standard-library module `json` (reads and writes JSON text) available; its contents are used as `json.name`.
- `from pathlib import Path`: brings `Path` (the class that represents a file or folder path as an object) from the standard-library module `pathlib` (file paths as objects) into this file, so it can be used without the module prefix.
- `from typing import Any`: brings `Any` (the type "anything", used where the shape is not known) from the standard-library module `typing` (names used in type hints) into this file, so it can be used without the module prefix.
- `from detect_respond.domain.detections import Detection`: brings `Detection` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.errors import InvalidDetectionError`: brings `InvalidDetectionError` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.posture import Acceptance, Finding`: brings `Acceptance`, `Finding` from another module of this project into this file, so it can be used without the module prefix.

From `src/detect_respond/infrastructure/files.py` (lines 14 to 16):

```python
class DetectionDirectory:
    """A `DetectionCatalog` over the `detections/` folder: one JSON file per detection and `alert-template.txt`."""

```

A class over the `detections/` folder: one JSON file per detection and `alert-template.txt`. It satisfies the `DetectionCatalog` protocol.

From `src/detect_respond/infrastructure/files.py` (lines 17 to 18):

```python
    def __init__(self, root: Path) -> None:
        self._root = root
```

The constructor: stores the folder path on the object.

From `src/detect_respond/infrastructure/files.py` (lines 20 to 29):

```python
    def detections(self) -> tuple[Detection, ...]:
        """Load and validate every `d*.json`, ordered by id; ids must be unique."""
        found = [
            Detection.from_mapping(json.loads(p.read_text(encoding="utf-8")))
            for p in sorted(self._root.glob("d*.json"))
        ]
        ids = [d.detection_id for d in found]
        if not found or len(ids) != len(set(ids)):
            raise InvalidDetectionError(f"{self._root} must hold detection files with unique ids")
        return tuple(sorted(found, key=lambda d: d.detection_id))
```

Loads and validates every `d*.json`, ordered by id. `found = [Detection.from_mapping(json.loads(p.read_text(encoding="utf-8"))) for p in sorted(self._root.glob("d*.json"))]` reads each file in name order and builds a detection. `ids = [...]`; `if not found or len(ids) != len(set(ids)): raise InvalidDetectionError(...)` requires at least one file and unique ids (a set drops repeats, so a different length means a repeat). The result is sorted by id.

From `src/detect_respond/infrastructure/files.py` (lines 31 to 33):

```python
    def template(self) -> str:
        """The alert template."""
        return (self._root / "alert-template.txt").read_text(encoding="utf-8")
```

Reads the alert template file as text.

From `src/detect_respond/infrastructure/files.py` (lines 36 to 38):

```python
class PostureFiles:
    """A `PostureSource` over findings files (`{"Findings": [...]}`, as `get-findings` prints them) and acceptances."""

```

A class over findings files (`{"Findings": [...]}`, as `get-findings` prints them) and the accepted-risks file. It satisfies the `PostureSource` protocol.

From `src/detect_respond/infrastructure/files.py` (lines 39 to 41):

```python
    def __init__(self, folder: Path, acceptances: Path) -> None:
        self._folder = folder
        self._acceptances = acceptances
```

The constructor: stores the findings folder and the acceptances file path.

From `src/detect_respond/infrastructure/files.py` (lines 43 to 47):

```python
    def findings(self, name: str) -> tuple[Finding, ...]:
        """Open failed findings from one file."""
        raw: dict[str, Any] = json.loads((self._folder / name).read_text(encoding="utf-8"))
        parsed = (Finding.from_asff(item) for item in raw["Findings"])
        return tuple(finding for finding in parsed if finding is not None)
```

Open failed findings from one file: `raw: dict[str, Any] = json.loads(...)`; `parsed = (Finding.from_asff(item) for item in raw["Findings"])` is a generator; `tuple(finding for finding in parsed if finding is not None)` keeps the real ones.

From `src/detect_respond/infrastructure/files.py` (lines 49 to 52):

```python
    def acceptances(self) -> tuple[Acceptance, ...]:
        """The accepted risks."""
        raw = json.loads(self._acceptances.read_text(encoding="utf-8"))
        return tuple(Acceptance(a["findingId"], a.get("reason", ""), a.get("acceptedOn", "")) for a in raw["accepted"])
```

The accepted risks: builds an `Acceptance` for each entry of `raw["accepted"]`, with `a.get("reason", "")` and `a.get("acceptedOn", "")` as defaults.

#### `src/detect_respond/infrastructure/plan_audit.py`

From `src/detect_respond/infrastructure/plan_audit.py` (line 1):

```python
"""Checks that the rules in a plan are the detections in `detections/`: the tested pattern is the deployed one."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/infrastructure/plan_audit.py` (lines 3 to 12):

```python
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from detect_respond.domain.detections import Detection
from detect_respond.domain.errors import PlanError
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `import json`: makes the standard-library module `json` (reads and writes JSON text) available; its contents are used as `json.name`.
- `from collections.abc import Mapping, Sequence`: brings `Mapping` (the type "dictionary-like, read only"), `Sequence` (the type "an ordered collection such as a list or tuple") from the standard-library module `collections.abc` (abstract types for collections, used in type hints) into this file, so it can be used without the module prefix.
- `from dataclasses import dataclass`: brings `dataclass` (the decorator that turns a class of fields into a class with a ready-made constructor, comparison and printout) from the standard-library module `dataclasses` (the dataclass helpers) into this file, so it can be used without the module prefix.
- `from pathlib import Path`: brings `Path` (the class that represents a file or folder path as an object) from the standard-library module `pathlib` (file paths as objects) into this file, so it can be used without the module prefix.
- `from typing import Any`: brings `Any` (the type "anything", used where the shape is not known) from the standard-library module `typing` (names used in type hints) into this file, so it can be used without the module prefix.
- `from detect_respond.domain.detections import Detection`: brings `Detection` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.errors import PlanError`: brings `PlanError` from another module of this project into this file, so it can be used without the module prefix.

From `src/detect_respond/infrastructure/plan_audit.py` (line 14):

```python
ALL_EVENTS_STATE = "ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS"
```

A constant: the rule state that includes read-only management events ([aws-eventbridge.md](aws-eventbridge.md)).

From `src/detect_respond/infrastructure/plan_audit.py` (line 15):

```python
_MODULE_PREFIX = {"global": "module.alerting_global", "home": "module.alerting_home", "watch": "module.alerting_watch"}
```

A dictionary from deployment place to the Terraform module name prefix used for it (`global` is `module.alerting_global`, and so on).

From `src/detect_respond/infrastructure/plan_audit.py` (lines 18 to 25):

```python
@dataclass(frozen=True)
class PlannedRule:
    """A rule as the plan would create it."""

    module: str
    name: str
    state: str
    pattern: Mapping[str, Any]
```

A frozen dataclass: an event rule as the plan would create it: module, name, state and pattern.

From `src/detect_respond/infrastructure/plan_audit.py` (lines 28 to 42):

```python
def planned_rules(plan: Mapping[str, Any]) -> tuple[PlannedRule, ...]:
    """The event rules that exist after the plan."""
    rules = []
    for change in plan.get("resource_changes", []):
        after = change["change"].get("after")
        if change["type"] == "aws_cloudwatch_event_rule" and after is not None:
            rules.append(
                PlannedRule(
                    change.get("module_address", ""),
                    after["name"],
                    after.get("state", "ENABLED"),
                    json.loads(after["event_pattern"]),
                )
            )
    return tuple(rules)
```

The event rules that exist after the plan: for each change of type `aws_cloudwatch_event_rule` with an `after` (not being deleted), a `PlannedRule` whose pattern is parsed with `json.loads(after["event_pattern"])` (the plan stores it as text; [json.md](json.md)).

From `src/detect_respond/infrastructure/plan_audit.py` (lines 45 to 71):

```python
def audit_rules(plan_path: Path, detections: Sequence[Detection]) -> list[str]:
    """Problems found: a detection with no rule where it should be deployed, a rule whose pattern differs from the
    detection's, or a rule that would miss read-only calls. Empty when the plan deploys exactly the detections."""
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    variables = {name: spec.get("value") for name, spec in plan.get("variables", {}).items()}
    rules = planned_rules(plan)
    if not rules:
        raise PlanError("the plan creates no event rules")
    problems = []
    for detection in detections:
        values = {p: str(variables.get(detection.parameter_variables.get(p, ""), "")) for p in detection.parameters}
        if detection.parameters and not all(values.values()):
            continue  # a parameterized detection is deployed only when its variable is set
        expected = detection.with_parameters(values).pattern
        for target in detection.deploy_to:
            where = [r for r in rules if r.module.startswith(_MODULE_PREFIX[target])]
            deployed = [r for r in where if r.name.endswith(f"-{detection.detection_id.lower()}")]
            if not deployed:
                problems.append(f"{detection.detection_id} is not deployed to {target}")
            for rule in deployed:
                if rule.pattern != expected:
                    problems.append(f"{detection.detection_id} in {rule.module} differs from detections/")
                if detection.include_read_only and rule.state != ALL_EVENTS_STATE:
                    problems.append(
                        f"{detection.detection_id} must use the rule state that includes read-only management events"
                    )
    return problems
```

Checks that the rules in a plan are the detections in `detections/`: the tested pattern is the deployed one. Returns a list of problems, empty when the plan deploys exactly the detections.

- `plan = json.loads(plan_path.read_text(encoding="utf-8"))` reads the plan; `variables` maps each plan variable name to its value; `rules = planned_rules(plan)`; `if not rules: raise PlanError(...)`.
- For each detection: `values = {p: str(variables.get(detection.parameter_variables.get(p, ""), "")) for p in detection.parameters}` finds the value of each placeholder from the plan's variables. `if detection.parameters and not all(values.values()): continue` skips a detection whose variable is not set (it is not deployed then).
- `expected = detection.with_parameters(values).pattern` is the pattern the rule should have.
- For each place in `detection.deploy_to`: `where` are the rules in that place's module; `deployed` those whose name ends with `-<id>`. No rule: the problem "is not deployed to <place>". For each deployed rule: a different pattern is "differs from detections/"; and if the detection needs read-only calls but the rule's state is not `ALL_EVENTS_STATE`, another problem.

#### `src/detect_respond/infrastructure/boto_revoker.py`

From `src/detect_respond/infrastructure/boto_revoker.py` (line 1):

```python
"""IAM through boto3, with timeouts and retries."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/infrastructure/boto_revoker.py` (lines 3 to 10):

```python
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import boto3
from botocore.config import Config
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `import json`: makes the standard-library module `json` (reads and writes JSON text) available; its contents are used as `json.name`.
- `from collections.abc import Mapping`: brings `Mapping` (the type "dictionary-like, read only") from the standard-library module `collections.abc` (abstract types for collections, used in type hints) into this file, so it can be used without the module prefix.
- `from typing import Any`: brings `Any` (the type "anything", used where the shape is not known) from the standard-library module `typing` (names used in type hints) into this file, so it can be used without the module prefix.
- `import boto3`: makes the library `boto3` (the library for calling AWS ([boto3.md](boto3.md))) available; its contents are used as `boto3.name`.
- `from botocore.config import Config`: brings `Config` from the library module `botocore.config` (the settings object for AWS clients) into this file, so it can be used without the module prefix.

From `src/detect_respond/infrastructure/boto_revoker.py` (lines 13 to 15):

```python
class BotoRevoker:
    """A `Revoker` over an IAM client."""

```

A class that satisfies the `Revoker` protocol with the AWS library ([boto3.md](boto3.md)). It is the only code in the package that changes an account.

From `src/detect_respond/infrastructure/boto_revoker.py` (lines 16 to 19):

```python
    def __init__(self, client: Any | None = None) -> None:
        self._iam = client or boto3.client(
            "iam", config=Config(retries={"max_attempts": 5, "mode": "standard"}, connect_timeout=3, read_timeout=10)
        )
```

The constructor. `client: Any | None = None` is an optional IAM client. `self._iam = client or boto3.client("iam", config=Config(...))` uses the client given (tests pass a stubbed one), otherwise builds a real one with `Config(retries={"max_attempts": 5, "mode": "standard"}, connect_timeout=3, read_timeout=10)`: up to 5 attempts with growing waits, and time limits in seconds so a call cannot hang.

From `src/detect_respond/infrastructure/boto_revoker.py` (lines 21 to 24):

```python
    def list_access_keys(self, user_name: str) -> tuple[str, ...]:
        """The ids of the user's access keys, active or not."""
        response = self._iam.list_access_keys(UserName=user_name)
        return tuple(item["AccessKeyId"] for item in response["AccessKeyMetadata"])
```

`response = self._iam.list_access_keys(UserName=user_name)` calls the service; `tuple(item["AccessKeyId"] for item in response["AccessKeyMetadata"])` returns only the key ids, so no AWS type leaks out of this file.

From `src/detect_respond/infrastructure/boto_revoker.py` (lines 26 to 28):

```python
    def put_role_policy(self, role_name: str, policy_name: str, policy: Mapping[str, Any]) -> None:
        """Attach (or replace) an inline policy; the call is idempotent."""
        self._iam.put_role_policy(RoleName=role_name, PolicyName=policy_name, PolicyDocument=json.dumps(policy))
```

Attaches (or replaces) an inline policy; the call is idempotent. The service wants the policy as JSON text, so `PolicyDocument=json.dumps(policy)` converts the dictionary.

From `src/detect_respond/infrastructure/boto_revoker.py` (lines 30 to 32):

```python
    def deactivate_access_key(self, user_name: str, access_key_id: str) -> None:
        """Set the key inactive; the call is idempotent."""
        self._iam.update_access_key(UserName=user_name, AccessKeyId=access_key_id, Status="Inactive")
```

Sets the key inactive with `update_access_key(..., Status="Inactive")`; the call is idempotent. The key is not deleted, so it can be examined later.

#### `src/detect_respond/interfaces/render.py`

From `src/detect_respond/interfaces/render.py` (line 1):

```python
"""Text and Markdown output: alerts, the timeline, measured times, archive check, posture table and review."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/interfaces/render.py` (lines 3 to 10):

```python
from __future__ import annotations

from detect_respond.application.use_cases import Alert, Drill
from detect_respond.domain.digest import DigestResult
from detect_respond.domain.drill import DrillMeasure, format_duration
from detect_respond.domain.events import AuditEvent
from detect_respond.domain.posture import SEVERITIES, Baseline
from detect_respond.domain.timeline import TimelineEntry
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `from detect_respond.application.use_cases import Alert, Drill`: brings `Alert`, `Drill` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.digest import DigestResult`: brings `DigestResult` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.drill import DrillMeasure, format_duration`: brings `DrillMeasure`, `format_duration` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.events import AuditEvent`: brings `AuditEvent` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.posture import SEVERITIES, Baseline`: brings `SEVERITIES`, `Baseline` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.timeline import TimelineEntry`: brings `TimelineEntry` from another module of this project into this file, so it can be used without the module prefix.

From `src/detect_respond/interfaces/render.py` (lines 13 to 23):

```python
def _target(event: AuditEvent) -> str:
    request = event.request
    if event.name == "AssumeRole":
        return f'{str(request.get("roleArn", "")).rsplit("/", 1)[-1]} session "{request.get("roleSessionName", "")}"'
    for field in ("userName", "bucketName", "roleName"):
        if field in request:
            acl = request.get("x-amz-acl")
            return f"{request[field]} ({acl[0]})" if field == "bucketName" and acl else str(request[field])
    if event.name.startswith("Describe"):
        return event.region
    return "-"
```

The "target" column of a timeline line. For `AssumeRole` it shows the role name and the session (`rsplit("/", 1)[-1]` cuts the ARN at the last slash and keeps the end). Otherwise the loop `for field in ("userName", "bucketName", "roleName"):` returns the first such request field, adding the ACL in brackets for a bucket call that sets one; a call whose name starts with `Describe` shows the Region; anything else shows a dash.

From `src/detect_respond/interfaces/render.py` (lines 26 to 27):

```python
def _clock(event: AuditEvent) -> str:
    return event.time.strftime("%H:%M:%S")
```

The time of an event as `HH:MM:SS`: `event.time.strftime("%H:%M:%S")` formats the datetime.

From `src/detect_respond/interfaces/render.py` (lines 30 to 36):

```python
def timeline_line(entry: TimelineEntry) -> str:
    """One line per call: time, name, target, result, and which detection it raises."""
    event = entry.event
    who = "(responder) " if entry.actor == "responder" else ""
    result = "DENIED" if event.denied else "OK"
    marks = f"  <- {', '.join(entry.detections)} fires" if entry.detections else ""
    return f"{_clock(event)}  {who}{event.name:<18} {_target(event):<40} {result:<7}{marks}".rstrip()
```

One line per call: time, name, target, result and which detection it raises. `who = "(responder) " if entry.actor == "responder" else ""` marks the responder's calls; `result = "DENIED" if event.denied else "OK"`; `marks` adds `<- D1 fires`; the f-string pads columns (`{event.name:<18}` pads to 18 characters, left-aligned) and `.rstrip()` removes trailing spaces.

From `src/detect_respond/interfaces/render.py` (lines 39 to 51):

```python
def measure_lines(measured: DrillMeasure) -> list[str]:
    """The two numbers, in the lesson's wording."""
    alert = f"first alert {_at(measured.first_alert)}" if measured.first_alert else "no alert"
    refused = (
        f"next call refused {_at(measured.contained_at)}"
        if measured.contained_at
        else "the attacker made no call after the revocation"
    )
    first = _at(measured.first_action)
    return [
        f"time to detect:  {format_duration(measured.time_to_detect)}  (first action {first}, {alert})",
        f"time to contain: {format_duration(measured.time_to_contain)}  (first action {first}, {refused})",
    ]
```

The two numbers in the lesson's wording. `alert` and `refused` build the explanatory parts (`f"first alert {_at(...)}" if measured.first_alert else "no alert"`), `first` is the first action's time, and the two returned lines show `format_duration(...)` for the time to detect and the time to contain.

From `src/detect_respond/interfaces/render.py` (lines 54 to 55):

```python
def _at(moment: object) -> str:
    return moment.strftime("%H:%M:%S") if hasattr(moment, "strftime") else str(moment)
```

Formats a moment as `HH:MM:SS` if it has a `strftime` method, otherwise as text (`hasattr(moment, "strftime")` asks whether the object has that method).

From `src/detect_respond/interfaces/render.py` (lines 58 to 60):

```python
def alert_blocks(alerts: tuple[Alert, ...]) -> str:
    """The alerts as the responder would receive them."""
    return "\n\n".join(alert.text.rstrip() for alert in alerts)
```

The alerts as the responder would receive them: the alert texts joined with a blank line (`"\n\n".join(alert.text.rstrip() for alert in alerts)`).

From `src/detect_respond/interfaces/render.py` (lines 63 to 72):

```python
def archive_lines(results: tuple[DigestResult, ...]) -> list[str]:
    """One line per digest, then a verdict."""
    lines = [
        f"digest {index}: {result.checked} files checked, {len(result.mismatched)} changed, "
        f"{len(result.missing)} missing"
        for index, result in enumerate(results, start=1)
    ]
    for result in results:
        lines += [f"  CHANGED {name}" for name in result.mismatched] + [f"  MISSING {name}" for name in result.missing]
    return lines
```

One line per digest, then a line per changed or missing file. `enumerate(results, start=1)` numbers the digests from 1; the second loop uses `lines += [...] + [...]` to append two lists at once.

From `src/detect_respond/interfaces/render.py` (lines 75 to 83):

```python
def posture_lines(result: Baseline) -> list[str]:
    """The baseline table of the lesson."""
    lines = ["severity    findings at start    after fixing    accepted with reason"]
    for severity in SEVERITIES:
        start, after, accepted = (
            counts.get(severity, 0) for counts in (result.start, result.after_fixing, result.accepted)
        )
        lines.append(f"{severity.lower():<11} {start:>17} {after:>15} {accepted:>23}")
    return lines
```

The baseline table of the lesson, as text lines. `start, after, accepted = (counts.get(severity, 0) for counts in (...))` unpacks three counts at once; `{start:>17}` right-aligns a number in a field of 17 characters.

From `src/detect_respond/interfaces/render.py` (lines 86 to 133):

```python
def review_markdown(drill: Drill, detections: dict[str, tuple[str, str]]) -> str:
    """A blameless review of the drill, built from the logs alone. `detections` maps an id to (title, prevention)."""
    lines = [
        "# Incident review: drill",
        "",
        "Blameless wording: the role allowed the calls below. Every claim cites an event id from the central archive.",
        "",
        "## Timeline, from the logs only",
        "",
        "| Time (UTC) | Actor | Call | Target | Result | Event id | Detection |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in drill.timeline:
        event = entry.event
        lines.append(
            f"| {_clock(event)} | {entry.actor} | {event.name} | {_target(event)} "
            f"| {'denied' if event.denied else 'ok'} | {event.event_id} | {', '.join(entry.detections) or '-'} |"
        )
    lines += [
        "",
        "## Times",
        "",
        *[f"- {line}" for line in measure_lines(drill.measured)],
        "",
        "## Prevented and only recorded",
        "",
    ]
    lines += [
        "| Detection | Raised by (event id) | Prevented? | What prevention would look like |",
        "| --- | --- | --- | --- |",
    ]
    for detection_id in drill.measured.detections:
        title, prevention = detections[detection_id]
        raised = [e for e in drill.timeline if detection_id in e.detections]
        prevented = all(entry.event.denied for entry in raised)
        cited = ", ".join(entry.event.event_id for entry in raised)
        outcome = "yes" if prevented else "no, recorded and alerted only"
        lines.append(f"| {detection_id} {title} | {cited} | {outcome} | {prevention} |")
    lines += [
        "",
        "## Changes that would stop the weakness recurring",
        "",
        *[f"- {detections[d][1]}" for d in drill.measured.detections if detections[d][1]],
        "- Remove the temporary exception (the drill user, the broad role and the drill bucket) and write down the "
        "time: `make down`.",
        "",
    ]
    return "\n".join(lines)
```

Builds the blameless review as Markdown text from the drill, using the logs alone ([markdown-and-mermaid.md](markdown-and-mermaid.md)). `detections` maps an id to (title, prevention).

- `lines = [...]` starts with the title, the blameless note, the heading "Timeline, from the logs only" and the table header.
- `for entry in drill.timeline:` adds one table row per call: time, actor, call, target, `denied` or `ok`, event id, detections.
- `lines += ["", "## Times", "", *[f"- {line}" for line in measure_lines(drill.measured)], ...]` adds the "Times" section; `*[...]` spreads the list items into the surrounding list.
- The "Prevented and only recorded" table has one row per detection that fired: `raised` are its timeline entries, `prevented = all(entry.event.denied for entry in raised)` is true if every call it raised was denied, and `outcome` says `yes` or `no, recorded and alerted only`.
- The last section lists the prevention advice and the reminder to remove the temporary exception with `make down`.
- `return "\n".join(lines)`.

#### `src/detect_respond/interfaces/cli.py`

From `src/detect_respond/interfaces/cli.py` (line 1):

```python
"""Command line for the detection and response work."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/interfaces/cli.py` (lines 3 to 19):

```python
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from detect_respond.application.use_cases import contain, posture_baseline, run_drill, scan_logs, verify_archive
from detect_respond.domain.errors import DetectRespondError
from detect_respond.domain.events import parse_time
from detect_respond.infrastructure.boto_revoker import BotoRevoker
from detect_respond.infrastructure.files import DetectionDirectory, PostureFiles
from detect_respond.infrastructure.log_archive import DirectoryArchive
from detect_respond.infrastructure.plan_audit import audit_rules
from detect_respond.interfaces import render
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `import argparse`: makes the standard-library module `argparse` (builds command-line options and sub-commands) available; its contents are used as `argparse.name`.
- `import json`: makes the standard-library module `json` (reads and writes JSON text) available; its contents are used as `json.name`.
- `import sys`: makes the standard-library module `sys` (access to the running program (arguments, standard error)) available; its contents are used as `sys.name`.
- `from collections.abc import Sequence`: brings `Sequence` (the type "an ordered collection such as a list or tuple") from the standard-library module `collections.abc` (abstract types for collections, used in type hints) into this file, so it can be used without the module prefix.
- `from datetime import UTC, datetime`: brings `UTC`, `datetime` from the standard-library module `datetime` (dates and times) into this file, so it can be used without the module prefix.
- `from pathlib import Path`: brings `Path` (the class that represents a file or folder path as an object) from the standard-library module `pathlib` (file paths as objects) into this file, so it can be used without the module prefix.
- `from detect_respond.application.use_cases import contain, posture_baseline, run_drill, scan_logs, verify_archive`: brings `contain`, `posture_baseline`, `run_drill`, `scan_logs`, `verify_archive` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.errors import DetectRespondError`: brings `DetectRespondError` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.events import parse_time`: brings `parse_time` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.infrastructure.boto_revoker import BotoRevoker`: brings `BotoRevoker` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.infrastructure.files import DetectionDirectory, PostureFiles`: brings `DetectionDirectory`, `PostureFiles` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.infrastructure.log_archive import DirectoryArchive`: brings `DirectoryArchive` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.infrastructure.plan_audit import audit_rules`: brings `audit_rules` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.interfaces import render`: brings `render` from another module of this project into this file, so it can be used without the module prefix.

From `src/detect_respond/interfaces/cli.py` (lines 22 to 24):

```python
class SystemClock:
    """The wall clock."""

```

A class for the wall clock; it satisfies the `Clock` protocol.

From `src/detect_respond/interfaces/cli.py` (lines 25 to 27):

```python
    def now(self) -> datetime:
        """The current time, timezone aware."""
        return datetime.now(UTC)
```

Returns `datetime.now(UTC)`, the current time with the UTC timezone attached.

From `src/detect_respond/interfaces/cli.py` (lines 30 to 38):

```python
def _add_drill_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--archive", type=Path, required=True, help="folder synced from the central log bucket")
    parser.add_argument("--detections", type=Path, default=Path("detections"))
    parser.add_argument("--role", default="drill-broad-role")
    parser.add_argument("--session", default="intruder", help="the attacker's role session name")
    parser.add_argument("--user", default="drill-user")
    parser.add_argument(
        "--alerts", type=Path, help='when each alert reached you: {"alerts": [{"eventId": ..., "receivedAt": ...}]}'
    )
```

Adds the options shared by the `drill` and `review` commands: `--archive` (required, a path), `--detections` (default `detections`), `--role` (default `drill-broad-role`), `--session` (default `intruder`), `--user` (default `drill-user`) and `--alerts` (optional). `type=Path` converts the text to a path.

From `src/detect_respond/interfaces/cli.py` (lines 41 to 83):

```python
def build_parser() -> argparse.ArgumentParser:
    """The argument parser, kept separate so tests can drive it."""
    parser = argparse.ArgumentParser(prog="detect-respond", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    scan = commands.add_parser("scan", help="run every detection over the archive and print the alerts")
    scan.add_argument("--archive", type=Path, required=True)
    scan.add_argument("--detections", type=Path, default=Path("detections"))
    scan.add_argument("--honeytoken-key-id", help="access key id of the honeytoken, for detection D5")
    scan.add_argument("--expect", help="comma-separated detection ids that must fire; exit 1 otherwise")

    drill = commands.add_parser(
        "drill", help="rebuild the timeline from the archive and measure time to detect and to contain"
    )
    _add_drill_arguments(drill)

    review = commands.add_parser("review", help="write or verify the blameless review of a drill")
    _add_drill_arguments(review)
    target = review.add_mutually_exclusive_group(required=True)
    target.add_argument("--output", type=Path)
    target.add_argument("--check", type=Path)

    stop = commands.add_parser("contain", help="revoke a role's sessions and a user's keys (a dry run unless --apply)")
    stop.add_argument("--role", default="drill-broad-role")
    stop.add_argument("--user", default="drill-user")
    stop.add_argument(
        "--access-key-id", action="append", default=[], help="key to deactivate; default: all the user's keys"
    )
    stop.add_argument("--apply", action="store_true", help="do it; without this flag nothing in the account changes")

    verify = commands.add_parser("verify-archive", help="check the log files against the digest files")
    verify.add_argument("--archive", type=Path, required=True)

    posture = commands.add_parser("posture", help="the findings baseline and the accepted risks")
    posture.add_argument("--findings", type=Path, required=True, help="folder with the findings files")
    posture.add_argument("--before", default="before.json")
    posture.add_argument("--after", default="after.json")
    posture.add_argument("--accepted", type=Path, required=True)

    audit = commands.add_parser("audit-rules", help="check that the plan deploys exactly the detections in detections/")
    audit.add_argument("--plan", type=Path, required=True)
    audit.add_argument("--detections", type=Path, default=Path("detections"))
    return parser
```

Builds the command-line parser (`argparse`), kept separate so tests can drive it. It defines seven sub-commands:

- `scan` (`--archive`, `--detections`, `--honeytoken-key-id`, `--expect`): run every detection over the archive.
- `drill`: rebuild the timeline and measure (the shared drill options).
- `review`: write or verify the review; a mutually exclusive group requires exactly one of `--output` or `--check`.
- `contain` (`--role`, `--user`, repeatable `--access-key-id` via `action="append"`, and `--apply` via `action="store_true"`, a flag that is false unless given).
- `verify-archive` (`--archive`).
- `posture` (`--findings`, `--before`, `--after`, `--accepted`).
- `audit-rules` (`--plan`, `--detections`).

From `src/detect_respond/interfaces/cli.py` (lines 86 to 102):

```python
def main(argv: Sequence[str] | None = None) -> int:
    """Run one command; exit 0 on success, 1 when a check failed, 2 on bad input."""
    args = build_parser().parse_args(argv)
    try:
        handler = {
            "scan": _scan,
            "drill": _drill,
            "review": _review,
            "contain": _contain,
            "verify-archive": _verify,
            "posture": _posture,
            "audit-rules": _audit,
        }[args.command]
        return handler(args)
    except (DetectRespondError, OSError, ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
```

Runs one command and returns its exit code: 0 success, 1 a check failed, 2 bad input.

- `args = build_parser().parse_args(argv)` parses the command line.
- `handler = {"scan": _scan, ...}[args.command]` looks the command up in a dictionary of functions; a function is a value that can be stored and called.
- `return handler(args)` runs it.
- `except (DetectRespondError, OSError, ValueError, KeyError) as error:` catches the package's own errors and four built-in ones, prints `error: ...` to standard error and returns 2. A real bug (any other exception) is not caught.

From `src/detect_respond/interfaces/cli.py` (lines 105 to 115):

```python
def _scan(args: argparse.Namespace) -> int:
    parameters = {"__HONEYTOKEN_ACCESS_KEY_ID__": args.honeytoken_key_id} if args.honeytoken_key_id else {}
    alerts = scan_logs(DirectoryArchive(args.archive), DetectionDirectory(args.detections), parameters)
    print(render.alert_blocks(alerts))
    fired = sorted({alert.detection.detection_id for alert in alerts})
    print(f"\n{len(alerts)} alerts from detections: {', '.join(fired) or 'none'}")
    missing = sorted(set(filter(None, (args.expect or "").split(","))) - set(fired))
    if missing:
        print(f"expected but did not fire: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0
```

The `scan` command. `parameters` holds the honeytoken placeholder only when `--honeytoken-key-id` was given. `alerts = scan_logs(DirectoryArchive(args.archive), DetectionDirectory(args.detections), parameters)` runs the scan; the alerts are printed. `fired` is the sorted set of detection ids that fired. `missing = sorted(set(filter(None, (args.expect or "").split(","))) - set(fired))` compares the ids named in `--expect` (split at commas; `filter(None, ...)` drops empty pieces) with those that fired; if any are missing, it prints them on standard error and returns 1.

From `src/detect_respond/interfaces/cli.py` (lines 118 to 124):

```python
def _alert_times(path: Path | None) -> dict[str, datetime]:
    if path is None:
        return {}
    return {
        item["eventId"]: parse_time(item["receivedAt"])
        for item in json.loads(path.read_text(encoding="utf-8"))["alerts"]
    }
```

Reads the optional alerts file ({"alerts": [{"eventId": ..., "receivedAt": ...}]}) into a dictionary from event id to a parsed time; with no path it returns an empty dictionary.

From `src/detect_respond/interfaces/cli.py` (lines 127 to 131):

```python
def _run(args: argparse.Namespace):  # type: ignore[no-untyped-def]
    catalog = DetectionDirectory(args.detections)
    return run_drill(
        DirectoryArchive(args.archive), catalog, args.role, args.session, args.user, _alert_times(args.alerts)
    ), catalog
```

Runs the drill for the `drill` and `review` commands and also returns the catalog. The comment `# type: ignore[no-untyped-def]` tells the type checker to accept the missing return annotation on this one line.

From `src/detect_respond/interfaces/cli.py` (lines 134 to 139):

```python
def _drill(args: argparse.Namespace) -> int:
    drill, _ = _run(args)
    print("\n".join(render.timeline_line(entry) for entry in drill.timeline))
    print()
    print("\n".join(render.measure_lines(drill.measured)))
    return 0 if drill.measured.time_to_contain is not None else 1
```

The `drill` command: prints the timeline lines, a blank line and the two measured lines, and returns 0 if a time to contain was measured, otherwise 1.

From `src/detect_respond/interfaces/cli.py` (lines 142 to 153):

```python
def _review(args: argparse.Namespace) -> int:
    drill, catalog = _run(args)
    text = render.review_markdown(drill, {d.detection_id: (d.title, d.prevention) for d in catalog.detections()})
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"wrote {args.output}")
        return 0
    if args.check.read_text(encoding="utf-8") != text:
        print(f"{args.check} is out of date: run `make review`", file=sys.stderr)
        return 1
    print(f"{args.check} is current")
    return 0
```

The `review` command: builds the review text (with a dictionary from detection id to (title, prevention)); with `--output` it writes the file; with `--check` it compares the file with the fresh text and returns 1 (telling to run `make review`) if they differ, otherwise 0.

From `src/detect_respond/interfaces/cli.py` (lines 156 to 160):

```python
def _contain(args: argparse.Namespace) -> int:
    result = contain(BotoRevoker(), SystemClock(), args.role, args.user, tuple(args.access_key_id), apply=args.apply)
    print(("applied" if result.applied else "dry run, nothing changed; to do it, add --apply") + ":")
    print("\n".join(result.plan.cli_commands()))
    return 0
```

The `contain` command: `result = contain(BotoRevoker(), SystemClock(), args.role, args.user, tuple(args.access_key_id), apply=args.apply)`. It prints `applied:` or `dry run, nothing changed; to do it, add --apply:` and then the CLI commands of the plan.

From `src/detect_respond/interfaces/cli.py` (lines 163 to 171):

```python
def _verify(args: argparse.Namespace) -> int:
    results = verify_archive(DirectoryArchive(args.archive))
    print("\n".join(render.archive_lines(results)))
    if not results:
        print("no digest files found", file=sys.stderr)
        return 1
    intact = all(result.intact for result in results)
    print("every logged file matches its digest" if intact else "the archive does not match its digests")
    return 0 if intact else 1
```

The `verify-archive` command: prints the digest lines; if there are no digest files it says so on standard error and returns 1; otherwise it prints whether every logged file matches its digest and returns 0 or 1.

From `src/detect_respond/interfaces/cli.py` (lines 174 to 181):

```python
def _posture(args: argparse.Namespace) -> int:
    result = posture_baseline(PostureFiles(args.findings, args.accepted), args.before, args.after)
    print("\n".join(render.posture_lines(result)))
    for finding_id in result.unaccepted_critical:
        print(f"critical and neither fixed nor accepted: {finding_id}", file=sys.stderr)
    for finding_id in result.reasonless:
        print(f"accepted without a reason: {finding_id}", file=sys.stderr)
    return 0 if result.meets_done_when else 1
```

The `posture` command: prints the baseline table, names on standard error the critical findings that are neither fixed nor accepted and the acceptances without a reason, and returns 0 only when the baseline meets the lesson's "done when".

From `src/detect_respond/interfaces/cli.py` (lines 184 to 189):

```python
def _audit(args: argparse.Namespace) -> int:
    problems = audit_rules(args.plan, DetectionDirectory(args.detections).detections())
    for problem in problems:
        print(f"problem: {problem}")
    print("the plan deploys exactly the detections in detections/" if not problems else f"{len(problems)} problems")
    return 0 if not problems else 1
```

The `audit-rules` command: prints each problem found by `audit_rules`, then a summary line, and returns 0 when there are none.

From `src/detect_respond/interfaces/cli.py` (lines 192 to 193):

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

`if __name__ == "__main__":` is true only when the file is run directly, not when it is imported. `raise SystemExit(main())` ends the program with the exit code.

#### `src/detect_respond/__main__.py`

From `src/detect_respond/__main__.py` (line 1):

```python
"""`python -m detect_respond` runs the command line."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `src/detect_respond/__main__.py` (line 3):

```python
from detect_respond.interfaces.cli import main
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from detect_respond.interfaces.cli import main`: brings `main` from another module of this project into this file, so it can be used without the module prefix.

From `src/detect_respond/__main__.py` (line 5):

```python
raise SystemExit(main())
```

`python -m detect_respond` runs this file. `main()` returns a number, and `raise SystemExit(number)` ends the program with it as the **exit code**: 0 means success, anything else a failure.

#### `src/detect_respond/__init__.py`

From `src/detect_respond/__init__.py` (line 1):

```python
"""Detection and response for a cloud account: detections as code, a timeline rebuilt from the logs, and containment."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

#### `src/detect_respond/application/__init__.py`

From `src/detect_respond/application/__init__.py` (line 1):

```python
"""Use cases: scan logs, rebuild a timeline, measure a drill, contain, verify the archive, baseline the posture."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

#### `src/detect_respond/domain/__init__.py`

From `src/detect_respond/domain/__init__.py` (line 1):

```python
"""Pure rules: events, the pattern matcher, detections, alerts, timeline, drill measures, containment, posture."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

#### `src/detect_respond/infrastructure/__init__.py`

From `src/detect_respond/infrastructure/__init__.py` (line 1):

```python
"""Adapters: the log archive on disk, detection and posture files, the plan reader, and IAM through boto3."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

#### `src/detect_respond/interfaces/__init__.py`

From `src/detect_respond/interfaces/__init__.py` (line 1):

```python
"""The command line and the text and Markdown rendering."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

### The fixture generator

`make fixtures` runs this script to write the synthetic audit archive and the posture findings.

#### `scripts/make_drill_fixtures.py`

From `scripts/make_drill_fixtures.py` (lines 1 to 5):

```python
"""Write the synthetic audit archive of the rehearsal into fixtures/drill, byte for byte the same on every run.

The events follow the lesson's drill timeline (documentation addresses, a placeholder account, made-up key ids). The
archive has the layout of the real bucket: log files per Region and day, and a digest file listing each file's hash.
"""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `scripts/make_drill_fixtures.py` (lines 7 to 14):

```python
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `import gzip`: makes the standard-library module `gzip` (reads and writes gzip-compressed files) available; its contents are used as `gzip.name`.
- `import hashlib`: makes the standard-library module `hashlib` (computes fingerprints such as SHA-256) available; its contents are used as `hashlib.name`.
- `import json`: makes the standard-library module `json` (reads and writes JSON text) available; its contents are used as `json.name`.
- `import sys`: makes the standard-library module `sys` (access to the running program (arguments, standard error)) available; its contents are used as `sys.name`.
- `from pathlib import Path`: brings `Path` (the class that represents a file or folder path as an object) from the standard-library module `pathlib` (file paths as objects) into this file, so it can be used without the module prefix.
- `from typing import Any`: brings `Any` (the type "anything", used where the shape is not known) from the standard-library module `typing` (names used in type hints) into this file, so it can be used without the module prefix.

From `scripts/make_drill_fixtures.py` (line 16):

```python
ACCOUNT = "000000000000"
```

Constants for the synthetic data: a placeholder account number, a documentation-range IP address (203.0.113.x is reserved for examples), and a user-agent text.

From `scripts/make_drill_fixtures.py` (line 17):

```python
SOURCE_IP = "203.0.113.25"
```

The source address written into the records.

From `scripts/make_drill_fixtures.py` (line 18):

```python
AGENT = "aws-cli/2.17.0 Python/3.12.4 command/iam.create-access-key"
```

The user-agent text written into the records.

From `scripts/make_drill_fixtures.py` (lines 19 to 24):

```python
USER = {
    "type": "IAMUser",
    "arn": f"arn:aws:iam::{ACCOUNT}:user/drill-user",
    "accessKeyId": "AKIADRILLEXAMPLE0001",
    "userName": "drill-user",
}
```

A dictionary: the `userIdentity` block of a call made by the drill user with its long-lived key (type, ARN, key id, user name).

From `scripts/make_drill_fixtures.py` (lines 25 to 29):

```python
INTRUDER = {
    "type": "AssumedRole",
    "arn": f"arn:aws:sts::{ACCOUNT}:assumed-role/drill-broad-role/intruder",
    "accessKeyId": "ASIADRILLEXAMPLE0001",
}
```

The identity block of a call made by the attacker's role session `intruder` (an assumed role; the key id starts with `ASIA` like all temporary keys).

From `scripts/make_drill_fixtures.py` (lines 30 to 34):

```python
RESPONDER = {
    "type": "AssumedRole",
    "arn": f"arn:aws:sts::{ACCOUNT}:assumed-role/security-admin/responder",
    "accessKeyId": "ASIARESPONDEREXAMPLE",
}
```

The identity block of the responder's session.

From `scripts/make_drill_fixtures.py` (lines 35 to 39):

```python
ADMIN = {
    "type": "AssumedRole",
    "arn": f"arn:aws:sts::{ACCOUNT}:assumed-role/sandbox-admin/setup",
    "accessKeyId": "ASIASETUPEXAMPLE0001",
}
```

The identity block of the administrator's setup session, which creates the weakness.

From `scripts/make_drill_fixtures.py` (line 40):

```python
ADMIN_POLICY = "arn:aws:iam::aws:policy/AdministratorAccess"
```

The ARN of AWS's managed policy `AdministratorAccess`.

From `scripts/make_drill_fixtures.py` (line 41):

```python
POWER_USER_POLICY = "arn:aws:iam::aws:policy/PowerUserAccess"
```

The ARN of AWS's managed policy `PowerUserAccess`.

From `scripts/make_drill_fixtures.py` (lines 44 to 71):

```python
def record(
    number: int,
    time: str,
    name: str,
    source: str,
    region: str,
    who: dict[str, str],
    request: dict[str, Any] | None,
    error: str | None = None,
    ip: str = SOURCE_IP,
) -> dict[str, Any]:
    """One CloudTrail-shaped record with a stable event id."""
    body: dict[str, Any] = {
        "eventVersion": "1.10",
        "eventID": f"00000000-0000-4000-8000-{number:012d}",
        "eventTime": time,
        "eventName": name,
        "eventSource": source,
        "awsRegion": region,
        "sourceIPAddress": ip,
        "userAgent": AGENT,
        "userIdentity": who,
        "requestParameters": request,
        "recipientAccountId": ACCOUNT,
    }
    if error:
        body["errorCode"] = error
    return body
```

Builds one CloudTrail-shaped record with a stable event id. `f"00000000-0000-4000-8000-{number:012d}"` writes the number padded with zeros to 12 digits, so the id is the same on every run. The dictionary holds the standard fields; `if error: body["errorCode"] = error` adds an error code only for a failed call.

From `scripts/make_drill_fixtures.py` (lines 74 to 176):

```python
def events() -> dict[str, list[dict[str, Any]]]:
    """The drill's events, grouped by the log file they are delivered in."""
    iam, s3, ec2, sts = "iam.amazonaws.com", "s3.amazonaws.com", "ec2.amazonaws.com", "sts.amazonaws.com"
    broad_role = f"arn:aws:iam::{ACCOUNT}:role/drill-broad-role"
    return {
        "us-east-1": [
            record(
                1,
                "2026-10-22T10:50:11Z",
                "AttachRolePolicy",
                iam,
                "us-east-1",
                ADMIN,
                {"roleName": "drill-broad-role", "policyArn": POWER_USER_POLICY},
                ip="198.51.100.7",
            ),
            record(
                2,
                "2026-10-22T10:52:30Z",
                "CreateAccessKey",
                iam,
                "us-east-1",
                ADMIN,
                {"userName": "drill-user"},
                ip="198.51.100.7",
            ),
            record(
                3,
                "2026-10-22T11:03:10Z",
                "AssumeRole",
                sts,
                "us-east-1",
                USER,
                {"roleArn": broad_role, "roleSessionName": "intruder"},
            ),
            record(
                5, "2026-10-22T11:03:42Z", "CreateAccessKey", iam, "us-east-1", INTRUDER, {"userName": "drill-user"}
            ),
            record(
                8,
                "2026-10-22T11:09:48Z",
                "PutRolePolicy",
                iam,
                "us-east-1",
                RESPONDER,
                {"roleName": "drill-broad-role", "policyName": "deny-all-before-now"},
                ip="198.51.100.7",
            ),
            record(
                9,
                "2026-10-22T11:09:57Z",
                "UpdateAccessKey",
                iam,
                "us-east-1",
                RESPONDER,
                {"userName": "drill-user", "accessKeyId": "AKIADRILLEXAMPLE0001", "status": "Inactive"},
                ip="198.51.100.7",
            ),
            record(
                10,
                "2026-10-22T11:10:02Z",
                "CreateAccessKey",
                iam,
                "us-east-1",
                INTRUDER,
                {"userName": "drill-user"},
                error="AccessDenied",
            ),
        ],
        "eu-west-1": [
            record(4, "2026-10-22T11:03:21Z", "ListBuckets", s3, "eu-west-1", INTRUDER, None),
            record(
                6,
                "2026-10-22T11:04:05Z",
                "PutBucketAcl",
                s3,
                "eu-west-1",
                INTRUDER,
                {"bucketName": f"drill-data-{ACCOUNT}", "x-amz-acl": ["public-read"]},
            ),
            record(
                11,
                "2026-10-22T11:20:00Z",
                "PutBucketAcl",
                s3,
                "eu-west-1",
                RESPONDER,
                {"bucketName": f"drill-data-{ACCOUNT}", "x-amz-acl": ["private"]},
                ip="198.51.100.7",
            ),
        ],
        "ap-southeast-2": [
            record(
                7,
                "2026-10-22T11:04:31Z",
                "DescribeInstances",
                ec2,
                "ap-southeast-2",
                INTRUDER,
                {"instancesSet": {}, "filterSet": {}},
            ),
        ],
    }
```

The drill's events, grouped by the log file (one per Region) they are delivered in: `us-east-1` (the IAM and role calls: the administrator attaches the policy and creates the key, the user assumes the role, the intruder creates a key, the responder revokes and deactivates, and the intruder's next call is denied), `eu-west-1` (the intruder lists buckets and makes the bucket public; the responder makes it private again) and `ap-southeast-2` (the intruder's call in an unused Region). `iam, s3, ec2, sts = ...` unpacks four names at once.

From `scripts/make_drill_fixtures.py` (lines 179 to 224):

```python
def write(target: Path) -> list[Path]:
    """Write the log files and the digest under `target` and return the paths."""
    written, listed = [], []
    for region, records in events().items():
        folder = f"AWSLogs/{ACCOUNT}/CloudTrail/{region}/2026/10/22"
        key = f"{folder}/{ACCOUNT}_CloudTrail_{region}_20261022T1130Z_drill.json.gz"
        content = json.dumps({"Records": records}, sort_keys=True, indent=2).encode()
        path = target / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(content, compresslevel=6, mtime=0))
        written.append(path)
        times = sorted(r["eventTime"] for r in records)
        listed.append(
            {
                "s3Object": key,
                "hashValue": hashlib.sha256(content).hexdigest(),
                "hashAlgorithm": "SHA-256",
                "newestEventTime": times[-1],
                "oldestEventTime": times[0],
            }
        )
    digest_folder = f"AWSLogs/{ACCOUNT}/CloudTrail-Digest/eu-west-1/2026/10/22"
    digest_key = f"{digest_folder}/{ACCOUNT}_CloudTrail-Digest_eu-west-1_drill_20261022T1140Z.json.gz"
    digest = {
        "awsAccountId": ACCOUNT,
        "digestStartTime": "2026-10-22T10:40:00Z",
        "digestEndTime": "2026-10-22T11:40:00Z",
        "digestPublicKeyFingerprint": "0000000000000000000000000000000000000000",
        "digestSignatureAlgorithm": "SHA256withRSA",
        "previousDigestHashValue": None,
        "logFiles": listed,
    }
    path = target / digest_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(digest, sort_keys=True, indent=2).encode(), compresslevel=6, mtime=0))
    written.append(path)
    alerts = {
        "alerts": [
            {"eventId": e["eventID"], "receivedAt": e["eventTime"]}
            for rs in events().values()
            for e in rs
            if e["eventID"][-2:] in {"05", "06", "07"}
        ]
    }
    (target / "alerts.json").write_text(json.dumps(alerts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return written
```

Writes the log files and the digest under `target` and returns the paths.

- For each Region: `folder` and `key` build the real bucket's layout; `content = json.dumps({"Records": records}, sort_keys=True, indent=2).encode()` serializes the records with sorted keys (so the bytes are the same every run) and `.encode()` turns the text into bytes; `path.parent.mkdir(parents=True, exist_ok=True)` creates the folders; `gzip.compress(content, compresslevel=6, mtime=0)` compresses with a fixed time stamp (`mtime=0`) so the compressed bytes are reproducible.
- `listed.append({...})` records, for the digest, the file's path, its SHA-256 fingerprint (`hashlib.sha256(content).hexdigest()`) and the oldest and newest event times.
- The digest dictionary has the fields of a real digest file (account, start and end time, a placeholder fingerprint, the signature algorithm and the list of log files); it is written the same way.
- `alerts` is the file of "when each alert reached the responder": it lists the events whose id ends in `05`, `06` or `07` (the three alerting calls), taking the event time as the arrival time; it is written with `write_text`.

From `scripts/make_drill_fixtures.py` (line 227):

```python
STANDARD = f"arn:aws:securityhub:eu-west-1:{ACCOUNT}:subscription/aws-foundational-security-best-practices/v/1.0.0"
```

The ARN prefix of the Foundational Security Best Practices standard, used in finding ids.

From `scripts/make_drill_fixtures.py` (lines 228 to 231):

```python
CRITICAL = [
    ("S3.2", "S3 buckets should prohibit public read access"),
    ("EC2.13", "Security groups should not allow ingress from 0.0.0.0/0 to port 22"),
]
```

Two example critical controls as (control id, title) pairs.

From `scripts/make_drill_fixtures.py` (lines 232 to 240):

```python
HIGH = [
    ("IAM.1", "IAM policies should not allow full administrative privileges"),
    ("IAM.6", "Hardware MFA should be enabled for the root user"),
    ("S3.5", "S3 buckets should require requests to use TLS"),
    ("S3.1", "S3 general purpose buckets should have block public access settings enabled"),
    ("EC2.2", "The VPC default security group should not allow inbound and outbound traffic"),
    ("CloudTrail.1", "CloudTrail should be enabled and configured with at least one multi-Region trail"),
    ("KMS.4", "KMS key rotation should be enabled"),
]
```

Seven example high controls as (control id, title) pairs.

From `scripts/make_drill_fixtures.py` (lines 243 to 252):

```python
def finding(number: int, control: str, title: str, severity: str) -> dict[str, Any]:
    """One finding in the posture service's format, reduced to the fields the baseline reads."""
    return {
        "Id": f"{STANDARD}/{control}/finding/00000000-0000-4000-8000-{number:012d}",
        "Title": f"{control} {title}",
        "Severity": {"Label": severity},
        "Compliance": {"Status": "FAILED"},
        "Workflow": {"Status": "NEW"},
        "Resources": [{"Id": f"arn:aws:s3:::example-resource-{number}"}],
    }
```

Builds one finding in the posture service's format, reduced to the fields the baseline reads: id, title, severity label, compliance status `FAILED`, workflow status `NEW` and one resource.

From `scripts/make_drill_fixtures.py` (lines 255 to 285):

```python
def write_posture(target: Path) -> list[Path]:
    """The lesson's example baseline: 2 critical and 7 high at the start; after fixing, 7 high, 5 of them accepted."""
    target.mkdir(parents=True, exist_ok=True)
    critical = [finding(i, c, t, "CRITICAL") for i, (c, t) in enumerate(CRITICAL, start=1)]
    high = [finding(i, c, t, "HIGH") for i, (c, t) in enumerate(HIGH, start=10)]
    files = {
        "before.json": {"Findings": critical + high},
        "after.json": {"Findings": high},
        "accepted.json": {
            "accepted": [
                {"findingId": f["Id"], "reason": reason, "acceptedOn": "2026-10-22"}
                for f, reason in zip(
                    high[2:],
                    [
                        "Sandbox bucket holds no data and is deleted the same day.",
                        "No workload serves traffic from this account.",
                        "The drill bucket is public on purpose; see the exception in the review.",
                        "A sandbox account has no multi-Region workload.",
                        "Key is deleted with the sandbox.",
                    ],
                    strict=True,
                )
            ]
        },
    }
    paths = []
    for name, body in files.items():
        path = target / name
        path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        paths.append(path)
    return paths
```

Writes the lesson's example baseline: `critical` and `high` are lists of findings built with `enumerate(..., start=...)` numbering them; `before.json` holds both, `after.json` only the high ones, and `accepted.json` pairs the last five high findings with a reason each (`zip(high[2:], [...], strict=True)` pairs two lists and raises an error if their lengths differ). Each file is written with sorted keys and a final newline.

From `scripts/make_drill_fixtures.py` (lines 288 to 294):

```python
def main() -> int:
    """Command line: make_drill_fixtures.py [fixtures_dir]; writes drill/ and posture/ under it."""
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures")
    archive = write(target / "drill")
    posture = write_posture(target / "posture")
    print(f"wrote {len(archive)} archive files, alerts.json and {len(posture)} posture files under {target}")
    return 0
```

The command line: `target = Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures")` takes the first argument or `fixtures`; it writes the drill archive and the posture files and prints a summary. `sys.argv` is the list of command-line words.

From `scripts/make_drill_fixtures.py` (lines 297 to 298):

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

Runs `main()` only when the file is started directly, and ends with its exit code.

### The tests

Tests are Python files too. Each function whose name starts with `test_` is one check; the helpers above them build test data.

#### `tests/builders.py`

From `tests/builders.py` (line 1):

```python
"""Builders for audit events and plans."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `tests/builders.py` (lines 3 to 7):

```python
from __future__ import annotations

from typing import Any

from detect_respond.domain.events import AuditEvent
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from __future__ import annotations`: a switch that keeps type hints as text instead of evaluating them when the file loads, so a class may name itself in a hint.
- `from typing import Any`: brings `Any` (the type "anything", used where the shape is not known) from the standard-library module `typing` (names used in type hints) into this file, so it can be used without the module prefix.
- `from detect_respond.domain.events import AuditEvent`: brings `AuditEvent` from another module of this project into this file, so it can be used without the module prefix.

From `tests/builders.py` (line 9):

```python
ACCOUNT = "000000000000"
```

Test constants. `ACCOUNT` is the placeholder account number.

From `tests/builders.py` (line 10):

```python
INTRUDER_ARN = f"arn:aws:sts::{ACCOUNT}:assumed-role/drill-broad-role/intruder"
```

The ARN of the attacker's role session, built with an f-string.

From `tests/builders.py` (lines 13 to 39):

```python
def event(
    name: str,
    *,
    source: str = "iam.amazonaws.com",
    region: str = "us-east-1",
    request: dict[str, Any] | None = None,
    arn: str = INTRUDER_ARN,
    access_key_id: str = "ASIAEXAMPLE000000001",
    error: str | None = None,
    time: str = "2026-10-22T11:03:42Z",
    event_id: str = "e-1",
) -> AuditEvent:
    """One audit event with sensible defaults."""
    record: dict[str, Any] = {
        "eventID": event_id,
        "eventTime": time,
        "eventName": name,
        "eventSource": source,
        "awsRegion": region,
        "sourceIPAddress": "203.0.113.25",
        "userAgent": "aws-cli/2.17.0",
        "userIdentity": {"arn": arn, "accessKeyId": access_key_id},
        "requestParameters": request,
    }
    if error:
        record["errorCode"] = error
    return AuditEvent.from_record(record)
```

Builds one audit event with sensible defaults. The `*` in the parameter list makes everything after `name` keyword-only. `record` is a dictionary shaped like an audit record; `if error: record["errorCode"] = error` adds the error only for a failed call; `AuditEvent.from_record(record)` parses it with the production code.

#### `tests/unit/detect_respond/test_cli_and_plan.py`

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 1 to 14):

```python
import gzip
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

from detect_respond.domain.errors import PlanError
from detect_respond.infrastructure.files import DetectionDirectory
from detect_respond.infrastructure.plan_audit import ALL_EVENTS_STATE, audit_rules
from detect_respond.interfaces import cli
from detect_respond.interfaces.cli import main
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `import gzip`: makes the standard-library module `gzip` (reads and writes gzip-compressed files) available; its contents are used as `gzip.name`.
- `import importlib.util`: makes the standard-library module `importlib.util` available; its contents are used as `importlib.util.name`.
- `import json`: makes the standard-library module `json` (reads and writes JSON text) available; its contents are used as `json.name`.
- `import shutil`: makes the standard-library module `shutil` (file operations) available; its contents are used as `shutil.name`.
- `import sys`: makes the standard-library module `sys` (access to the running program (arguments, standard error)) available; its contents are used as `sys.name`.
- `from pathlib import Path`: brings `Path` (the class that represents a file or folder path as an object) from the standard-library module `pathlib` (file paths as objects) into this file, so it can be used without the module prefix.
- `import pytest`: makes the library `pytest` (the test library) available; its contents are used as `pytest.name`.
- `from detect_respond.domain.errors import PlanError`: brings `PlanError` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.infrastructure.files import DetectionDirectory`: brings `DetectionDirectory` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.infrastructure.plan_audit import ALL_EVENTS_STATE, audit_rules`: brings `ALL_EVENTS_STATE`, `audit_rules` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.interfaces import cli`: brings `cli` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.interfaces.cli import main`: brings `main` from another module of this project into this file, so it can be used without the module prefix.

From `tests/unit/detect_respond/test_cli_and_plan.py` (line 16):

```python
DETECTIONS = DetectionDirectory(Path("detections")).detections()
```

Test data: the real detections, loaded from the `detections/` folder.

From `tests/unit/detect_respond/test_cli_and_plan.py` (line 17):

```python
ARCHIVE = "fixtures/drill"
```

Test data: the path of the committed rehearsal archive.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 20 to 26):

```python
def rule(module, detection_id, pattern, state="ENABLED"):
    name = f"{module.split('.')[1].replace('_', '-').replace('alerting-', 'detect-')}-{detection_id.lower()}"
    return {
        "type": "aws_cloudwatch_event_rule",
        "module_address": module,
        "change": {"after": {"name": name, "state": state, "event_pattern": json.dumps(pattern)}},
    }
```

A helper that builds a planned event rule: the `name` is made from the module address by text replacement; the `change.after` holds the name, the state and the pattern as JSON text.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 29 to 39):

```python
def full_plan(honeytoken="AKIAPLANONLY00000000"):
    by_id = {d.detection_id: d for d in DETECTIONS}
    filled = by_id["D5"].with_parameters({"__HONEYTOKEN_ACCESS_KEY_ID__": honeytoken})
    changes = [
        rule("module.alerting_global", "D1", by_id["D1"].pattern),
        rule("module.alerting_global", "D3", by_id["D3"].pattern),
        rule("module.alerting_global", "D5", filled.pattern),
        rule("module.alerting_home", "D2", by_id["D2"].pattern),
        rule("module.alerting_watch_ap_southeast_2", "D4", by_id["D4"].pattern, ALL_EVENTS_STATE),
    ]
    return {"variables": {"honeytoken_access_key_id": {"value": honeytoken}}, "resource_changes": changes}
```

A helper that builds a plan which deploys exactly the five detections: D5 is filled with a placeholder honeytoken key id; D1, D3 and D5 go to the global module, D2 to the home module and D4 to the watch module, with the wider state.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 42 to 45):

```python
def write(tmp_path, plan):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    return path
```

A helper that writes a plan dictionary as JSON into the test's temporary folder and returns the path.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 48 to 49):

```python
def test_a_plan_that_deploys_exactly_the_detections_has_no_problems(tmp_path):
    assert audit_rules(write(tmp_path, full_plan()), DETECTIONS) == []
```

A test: **a plan that deploys exactly the detections has no problems**. Each `assert` line states what must be true: `audit_rules(write(tmp_path, full_plan()), DETECTIONS) == []`. If one is false the test fails and `pytest` shows both sides of the comparison. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 52 to 55):

```python
def test_a_detection_missing_from_where_it_belongs_is_a_problem(tmp_path):
    plan = full_plan()
    plan["resource_changes"] = [c for c in plan["resource_changes"] if not c["change"]["after"]["name"].endswith("-d2")]
    assert audit_rules(write(tmp_path, plan), DETECTIONS) == ["D2 is not deployed to home"]
```

A test: **a detection missing from where it belongs is a problem**. Each `assert` line states what must be true: `audit_rules(write(tmp_path, plan), DETECTIONS) == ["D2 is not deployed to home"]`. If one is false the test fails and `pytest` shows both sides of the comparison. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 58 to 63):

```python
def test_a_rule_whose_pattern_drifted_from_the_file_is_a_problem(tmp_path):
    plan = full_plan()
    plan["resource_changes"][0]["change"]["after"]["event_pattern"] = json.dumps(
        {"detail": {"eventName": ["CreateAccessKey"]}}
    )
    assert audit_rules(write(tmp_path, plan), DETECTIONS) == ["D1 in module.alerting_global differs from detections/"]
```

A test: **a rule whose pattern drifted from the file is a problem**. Each `assert` line states what must be true: `audit_rules(write(tmp_path, plan), DETECTIONS) == ["D1 in module.alerting_global differs from detections/"]`. If one is false the test fails and `pytest` shows both sides of the comparison. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 66 to 71):

```python
def test_d4_without_the_all_events_state_is_a_problem(tmp_path):
    plan = full_plan()
    plan["resource_changes"][-1]["change"]["after"]["state"] = "ENABLED"
    assert audit_rules(write(tmp_path, plan), DETECTIONS) == [
        "D4 must use the rule state that includes read-only management events"
    ]
```

A test: **d4 without the all events state is a problem**. Each `assert` line states what must be true: `audit_rules(write(tmp_path, plan), DETECTIONS) == [`. If one is false the test fails and `pytest` shows both sides of the comparison. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 74 to 77):

```python
def test_the_honeytoken_detection_is_skipped_when_its_variable_is_empty(tmp_path):
    plan = full_plan(honeytoken="")
    plan["resource_changes"] = [c for c in plan["resource_changes"] if not c["change"]["after"]["name"].endswith("-d5")]
    assert audit_rules(write(tmp_path, plan), DETECTIONS) == []
```

A test: **the honeytoken detection is skipped when its variable is empty**. Each `assert` line states what must be true: `audit_rules(write(tmp_path, plan), DETECTIONS) == []`. If one is false the test fails and `pytest` shows both sides of the comparison. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 80 to 82):

```python
def test_a_plan_with_no_rules_is_an_error(tmp_path):
    with pytest.raises(PlanError, match="no event rules"):
        audit_rules(write(tmp_path, {"resource_changes": []}), DETECTIONS)
```

A test: **a plan with no rules is an error**. `with pytest.raises(PlanError, match="no event rules")` passes only if the code inside the block raises that error with a message matching the pattern. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 85 to 89):

```python
def test_scan_prints_alerts_and_checks_the_expected_detections(capsys):
    assert main(["scan", "--archive", ARCHIVE, "--expect", "D1,D2,D4"]) == 0
    output = capsys.readouterr().out
    assert "ALERT D1: new long-lived credential" in output
    assert "6 alerts from detections: D1, D2, D4" in output
```

A test: **scan prints alerts and checks the expected detections**. Each `assert` line states what must be true: `main(["scan", "--archive", ARCHIVE, "--expect", "D1,D2,D4"]) == 0`; `"ALERT D1: new long-lived credential" in output`; `"6 alerts from detections: D1, D2, D4" in output`. If one is false the test fails and `pytest` shows both sides of the comparison. `capsys` is a pytest fixture that captures what the code prints, so the test can read it.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 92 to 94):

```python
def test_scan_fails_when_an_expected_detection_does_not_fire(capsys):
    assert main(["scan", "--archive", ARCHIVE, "--expect", "D3"]) == 1
    assert "expected but did not fire: D3" in capsys.readouterr().err
```

A test: **scan fails when an expected detection does not fire**. Each `assert` line states what must be true: `main(["scan", "--archive", ARCHIVE, "--expect", "D3"]) == 1`; `"expected but did not fire: D3" in capsys.readouterr().err`. If one is false the test fails and `pytest` shows both sides of the comparison. `capsys` is a pytest fixture that captures what the code prints, so the test can read it.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 97 to 99):

```python
def test_scan_with_the_honeytoken_key_id_fires_d5(capsys):
    assert main(["scan", "--archive", ARCHIVE, "--honeytoken-key-id", "AKIADRILLEXAMPLE0001", "--expect", "D5"]) == 0
    assert "ALERT D5: honeytoken used" in capsys.readouterr().out
```

A test: **scan with the honeytoken key id fires d5**. Each `assert` line states what must be true: `main(["scan", "--archive", ARCHIVE, "--honeytoken-key-id", "AKIADRILLEXAMPLE0001", "--expect", "D5"]) == 0`; `"ALERT D5: honeytoken used" in capsys.readouterr().out`. If one is false the test fails and `pytest` shows both sides of the comparison. `capsys` is a pytest fixture that captures what the code prints, so the test can read it.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 102 to 108):

```python
def test_drill_prints_the_timeline_and_the_two_times(capsys):
    assert main(["drill", "--archive", ARCHIVE, "--alerts", f"{ARCHIVE}/alerts.json"]) == 0
    output = capsys.readouterr().out
    assert "11:03:42  CreateAccessKey" in output
    assert "<- D1 fires" in output
    assert "time to detect:  32 s" in output
    assert "time to contain: 6 min 52 s" in output
```

A test: **drill prints the timeline and the two times**. Each `assert` line states what must be true: `main(["drill", "--archive", ARCHIVE, "--alerts", f"{ARCHIVE}/alerts.json"]) == 0`; `"11:03:42  CreateAccessKey" in output`; `"<- D1 fires" in output`; `"time to detect:  32 s" in output`; `"time to contain: 6 min 52 s" in output`. If one is false the test fails and `pytest` shows both sides of the comparison. `capsys` is a pytest fixture that captures what the code prints, so the test can read it.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 111 to 113):

```python
def test_drill_without_an_attacker_session_exits_with_two(capsys):
    assert main(["drill", "--archive", ARCHIVE, "--session", "nobody"]) == 2
    assert "no call by the attacker" in capsys.readouterr().err
```

A test: **drill without an attacker session exits with two**. Each `assert` line states what must be true: `main(["drill", "--archive", ARCHIVE, "--session", "nobody"]) == 2`; `"no call by the attacker" in capsys.readouterr().err`. If one is false the test fails and `pytest` shows both sides of the comparison. `capsys` is a pytest fixture that captures what the code prints, so the test can read it.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 116 to 126):

```python
def test_review_is_written_then_verified_and_every_claim_cites_an_event(tmp_path, capsys):
    out = tmp_path / "review.md"
    common = ["review", "--archive", ARCHIVE, "--alerts", f"{ARCHIVE}/alerts.json"]
    assert main([*common, "--output", str(out)]) == 0
    assert main([*common, "--check", str(out)]) == 0
    text = out.read_text()
    assert "00000000-0000-4000-8000-000000000005" in text
    assert "no, recorded and alerted only" in text
    out.write_text("stale")
    assert main([*common, "--check", str(out)]) == 1
    assert "make review" in capsys.readouterr().err
```

A test: **review is written then verified and every claim cites an event**. Each `assert` line states what must be true: `main([*common, "--output", str(out)]) == 0`; `main([*common, "--check", str(out)]) == 0`; `"00000000-0000-4000-8000-000000000005" in text`; `"no, recorded and alerted only" in text`; `main([*common, "--check", str(out)]) == 1`; `"make review" in capsys.readouterr().err`. If one is false the test fails and `pytest` shows both sides of the comparison. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone. `capsys` is a pytest fixture that captures what the code prints, so the test can read it.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 129 to 143):

```python
def test_the_committed_review_is_current():
    assert (
        main(
            [
                "review",
                "--archive",
                ARCHIVE,
                "--alerts",
                f"{ARCHIVE}/alerts.json",
                "--check",
                "docs/REHEARSAL_REVIEW.md",
            ]
        )
        == 0
    )
```

A test: **the committed review is current**. Each `assert` line states what must be true: `(`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 146 to 152):

```python
def test_verify_archive_passes_on_the_fixture_and_fails_on_a_changed_file(tmp_path, capsys):
    assert main(["verify-archive", "--archive", ARCHIVE]) == 0
    shutil.copytree(ARCHIVE, tmp_path / "copy")
    log = next((tmp_path / "copy").rglob("*us-east-1*drill.json.gz"))
    log.write_bytes(log.read_bytes()[:-8] + b"tampered")
    assert main(["verify-archive", "--archive", str(tmp_path / "copy")]) in {1, 2}
    capsys.readouterr()
```

A test: **verify archive passes on the fixture and fails on a changed file**. Each `assert` line states what must be true: `main(["verify-archive", "--archive", ARCHIVE]) == 0`; `main(["verify-archive", "--archive", str(tmp_path / "copy")]) in {1, 2}`. If one is false the test fails and `pytest` shows both sides of the comparison. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone. `capsys` is a pytest fixture that captures what the code prints, so the test can read it.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 155 to 157):

```python
def test_verify_archive_without_digests_exits_with_one(tmp_path, capsys):
    assert main(["verify-archive", "--archive", str(tmp_path)]) == 1
    assert "no digest files" in capsys.readouterr().err
```

A test: **verify archive without digests exits with one**. Each `assert` line states what must be true: `main(["verify-archive", "--archive", str(tmp_path)]) == 1`; `"no digest files" in capsys.readouterr().err`. If one is false the test fails and `pytest` shows both sides of the comparison. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone. `capsys` is a pytest fixture that captures what the code prints, so the test can read it.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 160 to 168):

```python
def test_posture_passes_on_the_fixture_and_fails_with_an_open_critical(tmp_path, capsys):
    assert main(["posture", "--findings", "fixtures/posture", "--accepted", "fixtures/posture/accepted.json"]) == 0
    assert "critical                    2               0                       0" in capsys.readouterr().out
    shutil.copytree("fixtures/posture", tmp_path / "p")
    (tmp_path / "p" / "after.json").write_text((tmp_path / "p" / "before.json").read_text())
    assert (
        main(["posture", "--findings", str(tmp_path / "p"), "--accepted", str(tmp_path / "p" / "accepted.json")]) == 1
    )
    assert "critical and neither fixed nor accepted" in capsys.readouterr().err
```

A test: **posture passes on the fixture and fails with an open critical**. Each `assert` line states what must be true: `main(["posture", "--findings", "fixtures/posture", "--accepted", "fixtures/posture/accepted.json"]) == 0`; `"critical                    2               0                       0" in capsys.readouterr().out`; `(`; `"critical and neither fixed nor accepted" in capsys.readouterr().err`. If one is false the test fails and `pytest` shows both sides of the comparison. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone. `capsys` is a pytest fixture that captures what the code prints, so the test can read it.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 171 to 175):

```python
def test_contain_prints_a_dry_run_without_touching_the_account(capsys):
    assert main(["contain", "--access-key-id", "AKIADRILLEXAMPLE0001"]) == 0
    output = capsys.readouterr().out
    assert "dry run, nothing changed" in output
    assert "update-access-key --user-name drill-user --access-key-id AKIADRILLEXAMPLE0001 --status Inactive" in output
```

A test: **contain prints a dry run without touching the account**. Each `assert` line states what must be true: `main(["contain", "--access-key-id", "AKIADRILLEXAMPLE0001"]) == 0`; `"dry run, nothing changed" in output`; `"update-access-key --user-name drill-user --access-key-id AKIADRILLEXAMPLE0001 --status Inactive" in output`. If one is false the test fails and `pytest` shows both sides of the comparison. `capsys` is a pytest fixture that captures what the code prints, so the test can read it.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 178 to 194):

```python
def test_contain_with_apply_calls_the_revoker(monkeypatch, capsys):
    calls: list[tuple[str, ...]] = []

    class Recorder:
        def list_access_keys(self, user_name):
            return ()

        def put_role_policy(self, role_name, policy_name, policy):
            calls.append(("put", role_name, policy_name))

        def deactivate_access_key(self, user_name, access_key_id):
            calls.append(("deactivate", access_key_id))

    monkeypatch.setattr(cli, "BotoRevoker", Recorder)
    assert main(["contain", "--access-key-id", "AKIADRILLEXAMPLE0001", "--apply"]) == 0
    assert calls == [("put", "drill-broad-role", "deny-all-before-now"), ("deactivate", "AKIADRILLEXAMPLE0001")]
    assert capsys.readouterr().out.startswith("applied")
```

A test: **contain with apply calls the revoker**. Each `assert` line states what must be true: `main(["contain", "--access-key-id", "AKIADRILLEXAMPLE0001", "--apply"]) == 0`; `calls == [("put", "drill-broad-role", "deny-all-before-now"), ("deactivate", "AKIADRILLEXAMPLE0001")]`; `capsys.readouterr().out.startswith("applied")`. If one is false the test fails and `pytest` shows both sides of the comparison. `capsys` is a pytest fixture that captures what the code prints, so the test can read it. `monkeypatch` is a pytest fixture that changes an attribute or environment variable for this test only and restores it afterwards.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 197 to 198):

```python
def test_the_system_clock_is_timezone_aware():
    assert cli.SystemClock().now().tzinfo is not None
```

A test: **the system clock is timezone aware**. Each `assert` line states what must be true: `cli.SystemClock().now().tzinfo is not None`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 201 to 206):

```python
def test_audit_rules_command_reports_problems(tmp_path, capsys):
    plan = full_plan()
    plan["resource_changes"].pop(0)
    assert main(["audit-rules", "--plan", str(write(tmp_path, plan))]) == 1
    assert "problem: D1 is not deployed to global" in capsys.readouterr().out
    assert main(["audit-rules", "--plan", str(write(tmp_path, full_plan()))]) == 0
```

A test: **audit rules command reports problems**. Each `assert` line states what must be true: `main(["audit-rules", "--plan", str(write(tmp_path, plan))]) == 1`; `"problem: D1 is not deployed to global" in capsys.readouterr().out`; `main(["audit-rules", "--plan", str(write(tmp_path, full_plan()))]) == 0`. If one is false the test fails and `pytest` shows both sides of the comparison. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone. `capsys` is a pytest fixture that captures what the code prints, so the test can read it.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 209 to 211):

```python
def test_a_missing_directory_exits_with_two(tmp_path, capsys):
    assert main(["scan", "--archive", str(tmp_path / "missing"), "--detections", str(tmp_path / "none")]) == 2
    capsys.readouterr()
```

A test: **a missing directory exits with two**. Each `assert` line states what must be true: `main(["scan", "--archive", str(tmp_path / "missing"), "--detections", str(tmp_path / "none")]) == 2`. If one is false the test fails and `pytest` shows both sides of the comparison. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone. `capsys` is a pytest fixture that captures what the code prints, so the test can read it.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 214 to 216):

```python
def test_a_command_is_required():
    with pytest.raises(SystemExit):
        main([])
```

A test: **a command is required**. `with pytest.raises(SystemExit)` passes only if the code inside the block raises that error.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 219 to 229):

```python
def test_the_committed_fixtures_are_what_the_generator_writes(tmp_path):
    spec = importlib.util.spec_from_file_location("make_drill_fixtures", "scripts/make_drill_fixtures.py")
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules["make_drill_fixtures"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    module.write(tmp_path / "drill")
    module.write_posture(tmp_path / "posture")
    for generated in sorted(tmp_path.rglob("*")):
        if generated.is_file():
            committed = Path("fixtures") / generated.relative_to(tmp_path)
            assert _content(committed) == _content(generated), committed
```

A test: **the committed fixtures are what the generator writes**. Each `assert` line states what must be true: `_content(committed) == _content(generated), committed`. If one is false the test fails and `pytest` shows both sides of the comparison. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone.

From `tests/unit/detect_respond/test_cli_and_plan.py` (lines 232 to 234):

```python
def _content(path):
    """The content; gzip files by their uncompressed bytes, because compressed bytes depend on the zlib build."""
    return gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
```

Returns a file's content; gzip files by their uncompressed bytes, because compressed bytes depend on the compression library's build.

#### `tests/unit/detect_respond/test_drill.py`

From `tests/unit/detect_respond/test_drill.py` (lines 1 to 14):

```python
from datetime import timedelta
from pathlib import Path

import pytest

from detect_respond.application.use_cases import run_drill, scan_logs
from detect_respond.domain.alerts import render_alert
from detect_respond.domain.drill import format_duration, measure
from detect_respond.domain.errors import DrillError
from detect_respond.domain.events import parse_time
from detect_respond.domain.timeline import build_timeline
from detect_respond.infrastructure.files import DetectionDirectory
from detect_respond.infrastructure.log_archive import DirectoryArchive
from tests.builders import event
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `from datetime import timedelta`: brings `timedelta` from the standard-library module `datetime` (dates and times) into this file, so it can be used without the module prefix.
- `from pathlib import Path`: brings `Path` (the class that represents a file or folder path as an object) from the standard-library module `pathlib` (file paths as objects) into this file, so it can be used without the module prefix.
- `import pytest`: makes the library `pytest` (the test library) available; its contents are used as `pytest.name`.
- `from detect_respond.application.use_cases import run_drill, scan_logs`: brings `run_drill`, `scan_logs` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.alerts import render_alert`: brings `render_alert` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.drill import format_duration, measure`: brings `format_duration`, `measure` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.errors import DrillError`: brings `DrillError` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.events import parse_time`: brings `parse_time` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.timeline import build_timeline`: brings `build_timeline` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.infrastructure.files import DetectionDirectory`: brings `DetectionDirectory` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.infrastructure.log_archive import DirectoryArchive`: brings `DirectoryArchive` from another module of this project into this file, so it can be used without the module prefix.
- `from tests.builders import event`: brings `event` from another module of this project into this file, so it can be used without the module prefix.

From `tests/unit/detect_respond/test_drill.py` (line 16):

```python
ARCHIVE = DirectoryArchive(Path("fixtures/drill"))
```

Test data: the rehearsal archive opened as a `DirectoryArchive`.

From `tests/unit/detect_respond/test_drill.py` (line 17):

```python
CATALOG = DetectionDirectory(Path("detections"))
```

Test data: the detections folder as a catalog.

From `tests/unit/detect_respond/test_drill.py` (line 18):

```python
RULES = CATALOG.detections()
```

Test data: the catalog's detections.

From `tests/unit/detect_respond/test_drill.py` (lines 21 to 22):

```python
def drill(alert_times=None):
    return run_drill(ARCHIVE, CATALOG, "drill-broad-role", "intruder", "drill-user", alert_times or {})
```

A helper that runs the drill over the archive with the default role, session and user, and optional alert times.

From `tests/unit/detect_respond/test_drill.py` (lines 25 to 36):

```python
def test_the_timeline_is_rebuilt_from_the_archive_alone_denied_calls_included():
    entries = drill().timeline
    assert [(e.event.name, e.actor, e.event.denied) for e in entries] == [
        ("AssumeRole", "attacker", False),
        ("ListBuckets", "attacker", False),
        ("CreateAccessKey", "attacker", False),
        ("PutBucketAcl", "attacker", False),
        ("DescribeInstances", "attacker", False),
        ("PutRolePolicy", "responder", False),
        ("UpdateAccessKey", "responder", False),
        ("CreateAccessKey", "attacker", True),
    ]
```

A test: **the timeline is rebuilt from the archive alone denied calls included**. Each `assert` line states what must be true: `[(e.event.name, e.actor, e.event.denied) for e in entries] == [`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_drill.py` (lines 39 to 43):

```python
def test_setup_calls_and_other_principals_are_not_in_the_timeline():
    ids = {e.event.event_id[-2:] for e in drill().timeline}
    assert "01" not in ids
    assert "02" not in ids
    assert "11" not in ids
```

A test: **setup calls and other principals are not in the timeline**. Each `assert` line states what must be true: `"01" not in ids`; `"02" not in ids`; `"11" not in ids`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_drill.py` (lines 46 to 47):

```python
def test_the_detections_that_fire_are_the_lessons_d1_d2_d4():
    assert drill().measured.detections == ("D1", "D2", "D4")
```

A test: **the detections that fire are the lessons d1 d2 d4**. Each `assert` line states what must be true: `drill().measured.detections == ("D1", "D2", "D4")`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_drill.py` (lines 50 to 54):

```python
def test_time_to_detect_and_time_to_contain_match_the_lessons_example():
    measured = drill().measured
    assert measured.first_action == parse_time("2026-10-22T11:03:10Z")
    assert format_duration(measured.time_to_detect) == "32 s"
    assert format_duration(measured.time_to_contain) == "6 min 52 s"
```

A test: **time to detect and time to contain match the lessons example**. Each `assert` line states what must be true: `measured.first_action == parse_time("2026-10-22T11:03:10Z")`; `format_duration(measured.time_to_detect) == "32 s"`; `format_duration(measured.time_to_contain) == "6 min 52 s"`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_drill.py` (lines 57 to 61):

```python
def test_a_late_first_alert_hands_the_clock_to_the_next_detection_but_does_not_change_time_to_contain():
    delivered = {"00000000-0000-4000-8000-000000000005": parse_time("2026-10-22T11:05:10Z")}
    measured = drill(delivered).measured
    assert format_duration(measured.time_to_detect) == "55 s"  # the public-bucket alert (11:04:05) is now the first
    assert format_duration(measured.time_to_contain) == "6 min 52 s"
```

A test: **a late first alert hands the clock to the next detection but does not change time to contain**. Each `assert` line states what must be true: `format_duration(measured.time_to_detect) == "55 s"  # the public-bucket alert (11:04:05) is now the first`; `format_duration(measured.time_to_contain) == "6 min 52 s"`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_drill.py` (lines 64 to 70):

```python
def test_without_a_revocation_there_is_no_time_to_contain():
    events = [e for e in ARCHIVE.events() if e.name != "PutRolePolicy"]
    entries = build_timeline(events, RULES, "drill-broad-role", "intruder", "drill-user")
    measured = measure(entries, {})
    assert measured.revoked_at is None
    assert measured.contained_at is None
    assert format_duration(measured.time_to_contain) == "not measured"
```

A test: **without a revocation there is no time to contain**. Each `assert` line states what must be true: `measured.revoked_at is None`; `measured.contained_at is None`; `format_duration(measured.time_to_contain) == "not measured"`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_drill.py` (lines 73 to 78):

```python
def test_a_revocation_the_attacker_never_tests_leaves_containment_unconfirmed():
    events = [e for e in ARCHIVE.events() if e.event_id[-2:] != "10"]
    entries = build_timeline(events, RULES, "drill-broad-role", "intruder", "drill-user")
    measured = measure(entries, {})
    assert measured.revoked_at is not None
    assert measured.contained_at is None
```

A test: **a revocation the attacker never tests leaves containment unconfirmed**. Each `assert` line states what must be true: `measured.revoked_at is not None`; `measured.contained_at is None`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_drill.py` (lines 81 to 88):

```python
def test_no_attacker_calls_is_an_error():
    with pytest.raises(DrillError, match="no call"):
        measure(
            build_timeline(
                [event("ListBuckets", arn="arn:aws:iam::0:user/x")], RULES, "drill-broad-role", "intruder", "drill-user"
            ),
            {},
        )
```

A test: **no attacker calls is an error**. `with pytest.raises(DrillError, match="no call")` passes only if the code inside the block raises that error with a message matching the pattern.

From `tests/unit/detect_respond/test_drill.py` (lines 91 to 101):

```python
def test_a_session_with_no_detection_has_no_alert_time():
    entries = build_timeline(
        [event("ListBuckets", source="s3.amazonaws.com", region="eu-west-1")],
        RULES,
        "drill-broad-role",
        "intruder",
        "drill-user",
    )
    measured = measure(entries, {})
    assert measured.first_alert is None
    assert measured.time_to_detect is None
```

A test: **a session with no detection has no alert time**. Each `assert` line states what must be true: `measured.first_alert is None`; `measured.time_to_detect is None`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_drill.py` (lines 104 to 106):

```python
@pytest.mark.parametrize(("seconds", "text"), [(0, "0 s"), (59, "59 s"), (60, "1 min 0 s"), (412, "6 min 52 s")])
def test_durations_read_as_seconds_or_minutes_and_seconds(seconds, text):
    assert format_duration(timedelta(seconds=seconds)) == text
```

A test: **durations read as seconds or minutes and seconds**. The decorator `@pytest.mark.parametrize` runs the same test function once for each tuple in its list of cases, giving the named arguments the values of that tuple; each case appears as its own test result ([pytest.md](pytest.md)). Each `assert` line states what must be true: `format_duration(timedelta(seconds=seconds)) == text`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_drill.py` (lines 109 to 118):

```python
def test_scanning_the_archive_finds_every_firing_including_the_setup_key_and_the_retry():
    alerts = scan_logs(ARCHIVE, CATALOG, {})
    assert [(a.detection.detection_id, a.event.event_id[-2:]) for a in alerts] == [
        ("D1", "02"),
        ("D1", "05"),
        ("D2", "06"),
        ("D4", "07"),
        ("D1", "10"),
        ("D2", "11"),
    ]
```

A test: **scanning the archive finds every firing including the setup key and the retry**. Each `assert` line states what must be true: `[(a.detection.detection_id, a.event.event_id[-2:]) for a in alerts] == [`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_drill.py` (lines 121 to 123):

```python
def test_scanning_with_the_honeytoken_key_adds_d5():
    alerts = scan_logs(ARCHIVE, CATALOG, {"__HONEYTOKEN_ACCESS_KEY_ID__": "AKIADRILLEXAMPLE0001"})
    assert {a.detection.detection_id for a in alerts if a.event.access_key_id == "AKIADRILLEXAMPLE0001"} == {"D5"}
```

A test: **scanning with the honeytoken key adds d5**. Each `assert` line states what must be true: `{a.detection.detection_id for a in alerts if a.event.access_key_id == "AKIADRILLEXAMPLE0001"} == {"D5"}`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_drill.py` (lines 126 to 135):

```python
def test_an_alert_carries_who_what_from_where_and_the_first_step():
    first = scan_logs(ARCHIVE, CATALOG, {})[1]
    text = first.text
    assert text.startswith("ALERT D1: new long-lived credential")
    assert "who:      arn:aws:sts::000000000000:assumed-role/drill-broad-role/intruder" in text
    assert 'what:     iam.amazonaws.com CreateAccessKey {"userName":"drill-user"}' in text
    assert "from:     203.0.113.25" in text
    assert "first step: Ask who made it; disable it" in text
    assert "<" not in text
    assert "{" not in text.replace('{"userName":"drill-user"}', "")
```

A test: **an alert carries who what from where and the first step**. Each `assert` line states what must be true: `text.startswith("ALERT D1: new long-lived credential")`; `"who:      arn:aws:sts::000000000000:assumed-role/drill-broad-role/intruder" in text`; `'what:     iam.amazonaws.com CreateAccessKey {"userName":"drill-user"}' in text`; `"from:     203.0.113.25" in text`; `"first step: Ask who made it; disable it" in text`; `"<" not in text`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_drill.py` (lines 138 to 140):

```python
def test_an_event_with_no_request_renders_a_dash():
    quiet = event("ListBuckets", source="s3.amazonaws.com")
    assert "ListBuckets -" in render_alert(CATALOG.template(), RULES[0], quiet)
```

A test: **an event with no request renders a dash**. Each `assert` line states what must be true: `"ListBuckets -" in render_alert(CATALOG.template(), RULES[0], quiet)`. If one is false the test fails and `pytest` shows both sides of the comparison.

#### `tests/unit/detect_respond/test_pattern_and_detections.py`

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 1 to 10):

```python
import json
from pathlib import Path

import pytest

from detect_respond.domain.detections import Detection
from detect_respond.domain.errors import InvalidDetectionError, UnsupportedPatternError
from detect_respond.domain.pattern import matches
from detect_respond.infrastructure.files import DetectionDirectory
from tests.builders import event
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `import json`: makes the standard-library module `json` (reads and writes JSON text) available; its contents are used as `json.name`.
- `from pathlib import Path`: brings `Path` (the class that represents a file or folder path as an object) from the standard-library module `pathlib` (file paths as objects) into this file, so it can be used without the module prefix.
- `import pytest`: makes the library `pytest` (the test library) available; its contents are used as `pytest.name`.
- `from detect_respond.domain.detections import Detection`: brings `Detection` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.errors import InvalidDetectionError, UnsupportedPatternError`: brings `InvalidDetectionError`, `UnsupportedPatternError` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.pattern import matches`: brings `matches` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.infrastructure.files import DetectionDirectory`: brings `DetectionDirectory` from another module of this project into this file, so it can be used without the module prefix.
- `from tests.builders import event`: brings `event` from another module of this project into this file, so it can be used without the module prefix.

From `tests/unit/detect_respond/test_pattern_and_detections.py` (line 12):

```python
DETECTIONS = {d.detection_id: d for d in DetectionDirectory(Path("detections")).detections()}
```

Test data: the detections by id, as a dictionary comprehension.

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 15 to 45):

```python
@pytest.mark.parametrize(
    ("pattern", "target", "expected"),
    [
        ({"a": ["x"]}, {"a": "x"}, True),
        ({"a": ["x", "y"]}, {"a": "y"}, True),
        ({"a": ["x"]}, {"a": "z"}, False),
        ({"a": ["x"]}, {}, False),
        ({"a": [False]}, {"a": False}, True),
        ({"a": [False]}, {"a": True}, False),
        ({"a": ["x"]}, {"a": ["w", "x"]}, True),
        ({"a": {"b": ["x"]}}, {"a": {"b": "x"}}, True),
        ({"a": {"b": ["x"]}}, {"a": "x"}, False),
        ({"a": {"b": ["x"]}}, {}, False),
        ({"a": [{"anything-but": ["x"]}]}, {"a": "y"}, True),
        ({"a": [{"anything-but": ["x"]}]}, {"a": "x"}, False),
        ({"a": [{"anything-but": "x"}]}, {"a": "y"}, True),
        ({"a": [{"anything-but": ["x"]}]}, {}, False),
        ({"a": [{"prefix": "ab"}]}, {"a": "abc"}, True),
        ({"a": [{"prefix": "ab"}]}, {"a": "xab"}, False),
        ({"a": [{"suffix": "bc"}]}, {"a": "abc"}, True),
        ({"a": [{"suffix": "bc"}]}, {"a": 5}, False),
        ({"a": [{"exists": True}]}, {"a": None}, True),
        ({"a": [{"exists": False}]}, {}, True),
        ({"a": [{"exists": False}]}, {"a": 1}, False),
        ({"$or": [{"a": ["x"]}, {"b": ["y"]}]}, {"b": "y"}, True),
        ({"$or": [{"a": ["x"]}, {"b": ["y"]}]}, {"b": "z"}, False),
        ({"c": ["k"], "$or": [{"a": ["x"]}, {"b": ["y"]}]}, {"a": "x"}, False),
    ],
)
def test_the_matcher_follows_the_event_pattern_language(pattern, target, expected):
    assert matches(pattern, target) is expected
```

A test: **the matcher follows the event pattern language**. The decorator `@pytest.mark.parametrize` runs the same test function once for each tuple in its list of cases, giving the named arguments the values of that tuple; each case appears as its own test result ([pytest.md](pytest.md)). Each `assert` line states what must be true: `matches(pattern, target) is expected`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 48 to 51):

```python
@pytest.mark.parametrize("operator", [{"numeric": [">", 1]}, {"anything-but": "x", "prefix": "y"}])
def test_an_operator_the_matcher_does_not_implement_raises_instead_of_never_matching(operator):
    with pytest.raises(UnsupportedPatternError):
        matches({"a": [operator]}, {"a": 1})
```

A test: **an operator the matcher does not implement raises instead of never matching**. The decorator `@pytest.mark.parametrize` runs the same test function once for each tuple in its list of cases, giving the named arguments the values of that tuple; each case appears as its own test result ([pytest.md](pytest.md)). `with pytest.raises(UnsupportedPatternError)` passes only if the code inside the block raises that error.

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 54 to 57):

```python
def test_d1_fires_on_a_new_access_key_or_console_password_even_when_denied():
    assert DETECTIONS["D1"].fires(event("CreateAccessKey", request={"userName": "drill-user"}))
    assert DETECTIONS["D1"].fires(event("CreateLoginProfile", request={"userName": "drill-user"}))
    assert DETECTIONS["D1"].fires(event("CreateAccessKey", error="AccessDenied"))
```

A test: **d1 fires on a new access key or console password even when denied**. Each `assert` line states what must be true: `DETECTIONS["D1"].fires(event("CreateAccessKey", request={"userName": "drill-user"}))`; `DETECTIONS["D1"].fires(event("CreateLoginProfile", request={"userName": "drill-user"}))`; `DETECTIONS["D1"].fires(event("CreateAccessKey", error="AccessDenied"))`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 60 to 69):

```python
@pytest.mark.parametrize(
    "near_miss",
    [
        event("DeleteAccessKey"),
        event("ListAccessKeys"),
        event("CreateAccessKey", source="sts.amazonaws.com"),
    ],
)
def test_d1_ignores_near_misses(near_miss):
    assert not DETECTIONS["D1"].fires(near_miss)
```

A test: **d1 ignores near misses**. The decorator `@pytest.mark.parametrize` runs the same test function once for each tuple in its list of cases, giving the named arguments the values of that tuple; each case appears as its own test result ([pytest.md](pytest.md)). Each `assert` line states what must be true: `not DETECTIONS["D1"].fires(near_miss)`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 72 to 74):

```python
@pytest.mark.parametrize("name", ["PutBucketPolicy", "PutBucketAcl", "DeletePublicAccessBlock"])
def test_d2_fires_on_a_change_that_can_make_storage_public(name):
    assert DETECTIONS["D2"].fires(event(name, source="s3.amazonaws.com", region="eu-west-1"))
```

A test: **d2 fires on a change that can make storage public**. The decorator `@pytest.mark.parametrize` runs the same test function once for each tuple in its list of cases, giving the named arguments the values of that tuple; each case appears as its own test result ([pytest.md](pytest.md)). Each `assert` line states what must be true: `DETECTIONS["D2"].fires(event(name, source="s3.amazonaws.com", region="eu-west-1"))`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 77 to 96):

```python
def test_d2_fires_on_a_public_access_block_that_switches_a_setting_off_only():
    off = {
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": True,
        }
    }
    on = {
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        }
    }
    assert DETECTIONS["D2"].fires(event("PutPublicAccessBlock", source="s3.amazonaws.com", request=off))
    assert not DETECTIONS["D2"].fires(event("PutPublicAccessBlock", source="s3.amazonaws.com", request=on))
    assert not DETECTIONS["D2"].fires(event("PutBucketVersioning", source="s3.amazonaws.com"))
```

A test: **d2 fires on a public access block that switches a setting off only**. Each `assert` line states what must be true: `DETECTIONS["D2"].fires(event("PutPublicAccessBlock", source="s3.amazonaws.com", request=off))`; `not DETECTIONS["D2"].fires(event("PutPublicAccessBlock", source="s3.amazonaws.com", request=on))`; `not DETECTIONS["D2"].fires(event("PutBucketVersioning", source="s3.amazonaws.com"))`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 99 to 104):

```python
@pytest.mark.parametrize("name", ["AttachUserPolicy", "AttachRolePolicy", "AttachGroupPolicy"])
def test_d3_fires_only_when_the_administrator_policy_is_attached(name):
    admin = {"policyArn": "arn:aws:iam::aws:policy/AdministratorAccess"}
    power = {"policyArn": "arn:aws:iam::aws:policy/PowerUserAccess"}
    assert DETECTIONS["D3"].fires(event(name, request=admin))
    assert not DETECTIONS["D3"].fires(event(name, request=power))
```

A test: **d3 fires only when the administrator policy is attached**. The decorator `@pytest.mark.parametrize` runs the same test function once for each tuple in its list of cases, giving the named arguments the values of that tuple; each case appears as its own test result ([pytest.md](pytest.md)). Each `assert` line states what must be true: `DETECTIONS["D3"].fires(event(name, request=admin))`; `not DETECTIONS["D3"].fires(event(name, request=power))`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 107 to 111):

```python
def test_d4_fires_in_a_region_outside_the_list_and_for_read_only_calls():
    describe = event("DescribeInstances", source="ec2.amazonaws.com", region="ap-southeast-2")
    assert DETECTIONS["D4"].fires(describe)
    assert not DETECTIONS["D4"].fires(event("DescribeInstances", source="ec2.amazonaws.com", region="eu-west-1"))
    assert not DETECTIONS["D4"].fires(event("ListBuckets", source="s3.amazonaws.com", region="us-east-1"))
```

A test: **d4 fires in a region outside the list and for read only calls**. Each `assert` line states what must be true: `DETECTIONS["D4"].fires(describe)`; `not DETECTIONS["D4"].fires(event("DescribeInstances", source="ec2.amazonaws.com", region="eu-west-1"))`; `not DETECTIONS["D4"].fires(event("ListBuckets", source="s3.amazonaws.com", region="us-east-1"))`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 114 to 124):

```python
def test_d5_never_fires_until_its_placeholder_is_filled_then_fires_on_that_key_only():
    honeytoken = DETECTIONS["D5"]
    used = event("GetCallerIdentity", source="sts.amazonaws.com", access_key_id="AKIAHONEYTOKEN00001")
    assert not honeytoken.complete
    assert not honeytoken.fires(used)
    filled = honeytoken.with_parameters({"__HONEYTOKEN_ACCESS_KEY_ID__": "AKIAHONEYTOKEN00001"})
    assert filled.complete
    assert filled.fires(used)
    assert not filled.fires(
        event("GetCallerIdentity", source="sts.amazonaws.com", access_key_id="ASIAEXAMPLE000000001")
    )
```

A test: **d5 never fires until its placeholder is filled then fires on that key only**. Each `assert` line states what must be true: `not honeytoken.complete`; `not honeytoken.fires(used)`; `filled.complete`; `filled.fires(used)`; `not filled.fires(`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 127 to 132):

```python
def test_every_detection_has_a_severity_a_first_step_a_prevention_and_a_place_to_run():
    assert sorted(DETECTIONS) == ["D1", "D2", "D3", "D4", "D5"]
    for detection in DETECTIONS.values():
        assert detection.first_step
        assert detection.prevention
        assert detection.deploy_to
```

A test: **every detection has a severity a first step a prevention and a place to run**. Each `assert` line states what must be true: `sorted(DETECTIONS) == ["D1", "D2", "D3", "D4", "D5"]`; `detection.first_step`; `detection.prevention`; `detection.deploy_to`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 135 to 137):

```python
def raw_detection(**changes):
    base = json.loads(Path("detections/d1-new-long-lived-credential.json").read_text())
    return {**base, **changes}
```

A helper: the decoded JSON of detection D1 with some fields changed (`{**base, **changes}` merges two dictionaries, the later winning).

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 140 to 142):

```python
def test_a_detection_with_a_bad_severity_is_rejected():
    with pytest.raises(InvalidDetectionError, match="severity"):
        Detection.from_mapping(raw_detection(severity="urgent"))
```

A test: **a detection with a bad severity is rejected**. `with pytest.raises(InvalidDetectionError, match="severity")` passes only if the code inside the block raises that error with a message matching the pattern.

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 145 to 147):

```python
def test_a_detection_with_an_unknown_target_is_rejected():
    with pytest.raises(InvalidDetectionError, match="deployTo"):
        Detection.from_mapping(raw_detection(deployTo=["moon"]))
```

A test: **a detection with an unknown target is rejected**. `with pytest.raises(InvalidDetectionError, match="deployTo")` passes only if the code inside the block raises that error with a message matching the pattern.

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 150 to 154):

```python
def test_a_detection_missing_a_field_is_rejected():
    raw = raw_detection()
    del raw["pattern"]
    with pytest.raises(InvalidDetectionError, match="pattern"):
        Detection.from_mapping(raw)
```

A test: **a detection missing a field is rejected**. `with pytest.raises(InvalidDetectionError, match="pattern")` passes only if the code inside the block raises that error with a message matching the pattern.

From `tests/unit/detect_respond/test_pattern_and_detections.py` (lines 157 to 161):

```python
def test_a_folder_with_duplicate_ids_is_rejected(tmp_path):
    for name in ("d1-a.json", "d1-b.json"):
        (tmp_path / name).write_text(json.dumps(raw_detection()))
    with pytest.raises(InvalidDetectionError, match="unique"):
        DetectionDirectory(tmp_path).detections()
```

A test: **a folder with duplicate ids is rejected**. `with pytest.raises(InvalidDetectionError, match="unique")` passes only if the code inside the block raises that error with a message matching the pattern. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone.

#### `tests/unit/detect_respond/test_response.py`

From `tests/unit/detect_respond/test_response.py` (lines 1 to 19):

```python
import gzip
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import boto3
import pytest
from botocore.stub import Stubber

from detect_respond.application.use_cases import contain, posture_baseline, verify_archive
from detect_respond.domain.containment import POLICY_NAME, deny_sessions_before, plan_revocation
from detect_respond.domain.digest import verify_digest
from detect_respond.domain.errors import InvalidLogError
from detect_respond.domain.events import AuditEvent
from detect_respond.domain.posture import Acceptance, Finding, baseline
from detect_respond.infrastructure.boto_revoker import BotoRevoker
from detect_respond.infrastructure.files import PostureFiles
from detect_respond.infrastructure.log_archive import DirectoryArchive
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `import gzip`: makes the standard-library module `gzip` (reads and writes gzip-compressed files) available; its contents are used as `gzip.name`.
- `import json`: makes the standard-library module `json` (reads and writes JSON text) available; its contents are used as `json.name`.
- `import shutil`: makes the standard-library module `shutil` (file operations) available; its contents are used as `shutil.name`.
- `from datetime import UTC, datetime`: brings `UTC`, `datetime` from the standard-library module `datetime` (dates and times) into this file, so it can be used without the module prefix.
- `from pathlib import Path`: brings `Path` (the class that represents a file or folder path as an object) from the standard-library module `pathlib` (file paths as objects) into this file, so it can be used without the module prefix.
- `import boto3`: makes the library `boto3` (the library for calling AWS ([boto3.md](boto3.md))) available; its contents are used as `boto3.name`.
- `import pytest`: makes the library `pytest` (the test library) available; its contents are used as `pytest.name`.
- `from botocore.stub import Stubber`: brings `Stubber` from the library module `botocore.stub` (a way to replace the network with prepared answers in tests) into this file, so it can be used without the module prefix.
- `from detect_respond.application.use_cases import contain, posture_baseline, verify_archive`: brings `contain`, `posture_baseline`, `verify_archive` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.containment import POLICY_NAME, deny_sessions_before, plan_revocation`: brings `POLICY_NAME`, `deny_sessions_before`, `plan_revocation` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.digest import verify_digest`: brings `verify_digest` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.errors import InvalidLogError`: brings `InvalidLogError` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.events import AuditEvent`: brings `AuditEvent` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.domain.posture import Acceptance, Finding, baseline`: brings `Acceptance`, `Finding`, `baseline` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.infrastructure.boto_revoker import BotoRevoker`: brings `BotoRevoker` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.infrastructure.files import PostureFiles`: brings `PostureFiles` from another module of this project into this file, so it can be used without the module prefix.
- `from detect_respond.infrastructure.log_archive import DirectoryArchive`: brings `DirectoryArchive` from another module of this project into this file, so it can be used without the module prefix.

From `tests/unit/detect_respond/test_response.py` (line 21):

```python
NOW = datetime(2026, 10, 22, 11, 9, 48, tzinfo=UTC)
```

Test data: a fixed moment, 2026-10-22 11:09:48 UTC.

From `tests/unit/detect_respond/test_response.py` (line 24):

```python
class FakeClock:
```

A test double for the `Clock` protocol: a class whose `now()` always returns `NOW`.

From `tests/unit/detect_respond/test_response.py` (lines 25 to 26):

```python
    def now(self) -> datetime:
        return NOW
```

Returns the fixed moment.

From `tests/unit/detect_respond/test_response.py` (line 29):

```python
class FakeRevoker:
```

A test double for the `Revoker` protocol that records its calls in a list instead of calling the cloud.

From `tests/unit/detect_respond/test_response.py` (lines 30 to 32):

```python
    def __init__(self, keys=("AKIADRILLEXAMPLE0001", "AKIATWO")):
        self.keys = keys
        self.calls = []
```

The constructor: the key ids it will report and an empty list of calls.

From `tests/unit/detect_respond/test_response.py` (lines 34 to 36):

```python
    def list_access_keys(self, user_name):
        self.calls.append(("list", user_name))
        return self.keys
```

Records a `("list", user)` call and returns the keys.

From `tests/unit/detect_respond/test_response.py` (lines 38 to 39):

```python
    def put_role_policy(self, role_name, policy_name, policy):
        self.calls.append(("put", role_name, policy_name, policy["Statement"][0]["Condition"]))
```

Records a `("put", role, policy name, condition)` call.

From `tests/unit/detect_respond/test_response.py` (lines 41 to 42):

```python
    def deactivate_access_key(self, user_name, access_key_id):
        self.calls.append(("deactivate", user_name, access_key_id))
```

Records a `("deactivate", user, key)` call.

From `tests/unit/detect_respond/test_response.py` (lines 45 to 50):

```python
def test_the_revocation_denies_every_session_issued_before_the_moment_and_only_those():
    policy = deny_sessions_before(NOW)
    statement = policy["Statement"][0]
    assert statement["Effect"] == "Deny"
    assert statement["Action"] == "*"
    assert statement["Condition"] == {"DateLessThan": {"aws:TokenIssueTime": "2026-10-22T11:09:48Z"}}
```

A test: **the revocation denies every session issued before the moment and only those**. Each `assert` line states what must be true: `statement["Effect"] == "Deny"`; `statement["Action"] == "*"`; `statement["Condition"] == {"DateLessThan": {"aws:TokenIssueTime": "2026-10-22T11:09:48Z"}}`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_response.py` (lines 53 to 60):

```python
def test_the_moment_is_written_in_utc_whatever_the_zone_of_the_clock():
    from datetime import timedelta, timezone

    local = datetime(2026, 10, 22, 13, 9, 48, tzinfo=timezone(timedelta(hours=2)))
    assert (
        deny_sessions_before(local)["Statement"][0]["Condition"]["DateLessThan"]["aws:TokenIssueTime"]
        == "2026-10-22T11:09:48Z"
    )
```

A test: **the moment is written in utc whatever the zone of the clock**. Each `assert` line states what must be true: `(`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_response.py` (lines 63 to 68):

```python
def test_a_dry_run_plans_and_changes_nothing():
    revoker = FakeRevoker()
    result = contain(revoker, FakeClock(), "drill-broad-role", "drill-user", (), apply=False)
    assert not result.applied
    assert result.plan.access_key_ids == ("AKIADRILLEXAMPLE0001", "AKIATWO")
    assert revoker.calls == [("list", "drill-user")]
```

A test: **a dry run plans and changes nothing**. Each `assert` line states what must be true: `not result.applied`; `result.plan.access_key_ids == ("AKIADRILLEXAMPLE0001", "AKIATWO")`; `revoker.calls == [("list", "drill-user")]`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_response.py` (lines 71 to 75):

```python
def test_applying_revokes_the_sessions_first_and_then_every_key():
    revoker = FakeRevoker()
    contain(revoker, FakeClock(), "drill-broad-role", "drill-user", (), apply=True)
    assert [call[0] for call in revoker.calls] == ["list", "put", "deactivate", "deactivate"]
    assert revoker.calls[1][:3] == ("put", "drill-broad-role", POLICY_NAME)
```

A test: **applying revokes the sessions first and then every key**. Each `assert` line states what must be true: `[call[0] for call in revoker.calls] == ["list", "put", "deactivate", "deactivate"]`; `revoker.calls[1][:3] == ("put", "drill-broad-role", POLICY_NAME)`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_response.py` (lines 78 to 81):

```python
def test_given_key_ids_are_used_without_listing():
    revoker = FakeRevoker()
    contain(revoker, FakeClock(), "r", "u", ("AKIAGIVEN",), apply=True)
    assert [call[0] for call in revoker.calls] == ["put", "deactivate"]
```

A test: **given key ids are used without listing**. Each `assert` line states what must be true: `[call[0] for call in revoker.calls] == ["put", "deactivate"]`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_response.py` (lines 84 to 93):

```python
def test_the_plan_prints_the_same_actions_as_cli_commands():
    commands = plan_revocation("drill-broad-role", "drill-user", ("AKIADRILLEXAMPLE0001",), NOW).cli_commands()
    assert commands[0].startswith(
        "aws iam put-role-policy --role-name drill-broad-role --policy-name deny-all-before-now"
    )
    assert "aws:TokenIssueTime" in commands[0]
    assert (
        commands[1]
        == "aws iam update-access-key --user-name drill-user --access-key-id AKIADRILLEXAMPLE0001 --status Inactive"
    )
```

A test: **the plan prints the same actions as cli commands**. Each `assert` line states what must be true: `commands[0].startswith(`; `"aws:TokenIssueTime" in commands[0]`; `(`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_response.py` (lines 96 to 115):

```python
def test_the_boto_revoker_makes_the_three_iam_calls():
    iam = boto3.client("iam", region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="x")
    document = deny_sessions_before(NOW)
    with Stubber(iam) as stub:
        stub.add_response(
            "list_access_keys",
            {"AccessKeyMetadata": [{"AccessKeyId": "AKIADRILLEXAMPLE0001"}], "IsTruncated": False},
            {"UserName": "u"},
        )
        stub.add_response(
            "put_role_policy", {}, {"RoleName": "r", "PolicyName": "p", "PolicyDocument": json.dumps(document)}
        )
        stub.add_response(
            "update_access_key", {}, {"UserName": "u", "AccessKeyId": "AKIADRILLEXAMPLE0001", "Status": "Inactive"}
        )
        revoker = BotoRevoker(iam)
        assert revoker.list_access_keys("u") == ("AKIADRILLEXAMPLE0001",)
        revoker.put_role_policy("r", "p", document)
        revoker.deactivate_access_key("u", "AKIADRILLEXAMPLE0001")
        stub.assert_no_pending_responses()
```

A test: **the boto revoker makes the three iam calls**. Each `assert` line states what must be true: `revoker.list_access_keys("u") == ("AKIADRILLEXAMPLE0001",)`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_response.py` (lines 118 to 120):

```python
def test_the_default_boto_revoker_builds_its_own_client(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    assert BotoRevoker() is not None
```

A test: **the default boto revoker builds its own client**. Each `assert` line states what must be true: `BotoRevoker() is not None`. If one is false the test fails and `pytest` shows both sides of the comparison. `monkeypatch` is a pytest fixture that changes an attribute or environment variable for this test only and restores it afterwards.

From `tests/unit/detect_respond/test_response.py` (lines 123 to 125):

```python
def test_an_untouched_archive_matches_its_digest():
    results = verify_archive(DirectoryArchive(Path("fixtures/drill")))
    assert [(r.checked, r.intact) for r in results] == [(3, True)]
```

A test: **an untouched archive matches its digest**. Each `assert` line states what must be true: `[(r.checked, r.intact) for r in results] == [(3, True)]`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_response.py` (lines 128 to 132):

```python
def tampered_copy(tmp_path, change):
    shutil.copytree("fixtures/drill", tmp_path / "archive")
    log = next((tmp_path / "archive").rglob("*eu-west-1*drill.json.gz"))
    change(log)
    return DirectoryArchive(tmp_path / "archive")
```

A helper: copies the whole rehearsal archive into the test's folder (`shutil.copytree`), finds one log file (`next(... .rglob("*eu-west-1*drill.json.gz"))`), lets the given function change it, and returns an archive over the copy.

From `tests/unit/detect_respond/test_response.py` (lines 135 to 143):

```python
def test_an_altered_log_file_no_longer_matches_its_digest(tmp_path):
    def alter(log):
        text = gzip.decompress(log.read_bytes()).decode().replace("public-read", "private")
        log.write_bytes(gzip.compress(text.encode(), mtime=0))

    result = verify_archive(tampered_copy(tmp_path, alter))[0]
    assert not result.intact
    assert len(result.mismatched) == 1
    assert "eu-west-1" in result.mismatched[0]
```

A test: **an altered log file no longer matches its digest**. Each `assert` line states what must be true: `not result.intact`; `len(result.mismatched) == 1`; `"eu-west-1" in result.mismatched[0]`. If one is false the test fails and `pytest` shows both sides of the comparison. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone.

From `tests/unit/detect_respond/test_response.py` (lines 146 to 149):

```python
def test_a_deleted_log_file_is_reported_missing(tmp_path):
    result = verify_archive(tampered_copy(tmp_path, lambda log: log.unlink()))[0]
    assert len(result.missing) == 1
    assert not result.intact
```

A test: **a deleted log file is reported missing**. Each `assert` line states what must be true: `len(result.missing) == 1`; `not result.intact`. If one is false the test fails and `pytest` shows both sides of the comparison. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone.

From `tests/unit/detect_respond/test_response.py` (lines 152 to 156):

```python
def test_the_digest_compares_hashes_case_insensitively():
    import hashlib

    digest = {"logFiles": [{"s3Object": "a", "hashValue": hashlib.sha256(b"x").hexdigest().upper()}]}
    assert verify_digest(digest, lambda key: b"x").intact
```

A test: **the digest compares hashes case insensitively**. Each `assert` line states what must be true: `verify_digest(digest, lambda key: b"x").intact`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_response.py` (lines 159 to 162):

```python
def test_a_file_that_is_not_json_is_a_named_error(tmp_path):
    (tmp_path / "broken.json").write_text("{not json")
    with pytest.raises(InvalidLogError, match=r"broken\.json"):
        list(DirectoryArchive(tmp_path).events())
```

A test: **a file that is not json is a named error**. `with pytest.raises(InvalidLogError, match=r"broken\.json")` passes only if the code inside the block raises that error with a message matching the pattern. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone.

From `tests/unit/detect_respond/test_response.py` (lines 165 to 167):

```python
def test_a_record_without_an_event_id_is_a_named_error():
    with pytest.raises(InvalidLogError, match="eventID"):
        AuditEvent.from_record({"eventTime": "2026-10-22T11:03:42Z"})
```

A test: **a record without an event id is a named error**. `with pytest.raises(InvalidLogError, match="eventID")` passes only if the code inside the block raises that error with a message matching the pattern.

From `tests/unit/detect_respond/test_response.py` (lines 170 to 176):

```python
def test_a_lookup_events_entry_wrapping_a_record_parses():
    wrapped = {
        "CloudTrailEvent": json.dumps(
            {"eventID": "x", "eventTime": "2026-10-22T11:03:42Z", "eventName": "N", "eventSource": "iam.amazonaws.com"}
        )
    }
    assert AuditEvent.from_record(wrapped).event_id == "x"
```

A test: **a lookup events entry wrapping a record parses**. Each `assert` line states what must be true: `AuditEvent.from_record(wrapped).event_id == "x"`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_response.py` (lines 179 to 183):

```python
def test_a_bare_list_of_records_in_a_plain_file_is_read(tmp_path):
    record = {"eventID": "x", "eventTime": "2026-10-22T11:03:42Z", "eventName": "N", "eventSource": "iam.amazonaws.com"}
    (tmp_path / "events.json").write_text(json.dumps([record]))
    assert [e.event_id for e in DirectoryArchive(tmp_path).events()] == ["x"]
    assert DirectoryArchive(tmp_path).read_log("events.json") == json.dumps([record]).encode()
```

A test: **a bare list of records in a plain file is read**. Each `assert` line states what must be true: `[e.event_id for e in DirectoryArchive(tmp_path).events()] == ["x"]`; `DirectoryArchive(tmp_path).read_log("events.json") == json.dumps([record]).encode()`. If one is false the test fails and `pytest` shows both sides of the comparison. `tmp_path` is a pytest fixture: a fresh, empty temporary folder for this test alone.

From `tests/unit/detect_respond/test_response.py` (lines 186 to 194):

```python
def asff(finding_id, severity, status="FAILED", workflow="NEW"):
    return {
        "Id": finding_id,
        "Title": finding_id,
        "Severity": {"Label": severity},
        "Compliance": {"Status": status},
        "Workflow": {"Status": workflow},
        "Resources": [{"Id": "r"}],
    }
```

A helper that builds a finding dictionary in the posture format with the given id, severity, compliance status and workflow status.

From `tests/unit/detect_respond/test_response.py` (lines 197 to 202):

```python
def test_only_open_failures_are_findings():
    assert Finding.from_asff(asff("a", "HIGH")) is not None
    assert Finding.from_asff(asff("a", "HIGH", status="PASSED")) is None
    assert Finding.from_asff(asff("a", "HIGH", workflow="SUPPRESSED")) is None
    assert Finding.from_asff(asff("a", "HIGH", workflow="RESOLVED")) is None
    assert Finding.from_asff({**asff("a", "HIGH"), "Resources": []}).resource == ""  # type: ignore[union-attr]
```

A test: **only open failures are findings**. Each `assert` line states what must be true: `Finding.from_asff(asff("a", "HIGH")) is not None`; `Finding.from_asff(asff("a", "HIGH", status="PASSED")) is None`; `Finding.from_asff(asff("a", "HIGH", workflow="SUPPRESSED")) is None`; `Finding.from_asff(asff("a", "HIGH", workflow="RESOLVED")) is None`; `Finding.from_asff({**asff("a", "HIGH"), "Resources": []}).resource == ""  # type: ignore[union-attr]`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_response.py` (lines 205 to 214):

```python
def test_the_baseline_counts_open_accepted_and_fixed_findings():
    start = [Finding(f"c{i}", "t", "CRITICAL", "r") for i in range(2)] + [
        Finding(f"h{i}", "t", "HIGH", "r") for i in range(7)
    ]
    after = [Finding(f"h{i}", "t", "HIGH", "r") for i in range(7)]
    accepted = [Acceptance(f"h{i}", "sandbox only", "2026-10-22") for i in range(2, 7)]
    result = baseline(start, after, accepted)
    assert (result.start["CRITICAL"], result.after_fixing["CRITICAL"], result.accepted["CRITICAL"]) == (2, 0, 0)
    assert (result.start["HIGH"], result.after_fixing["HIGH"], result.accepted["HIGH"]) == (7, 2, 5)
    assert result.meets_done_when
```

A test: **the baseline counts open accepted and fixed findings**. Each `assert` line states what must be true: `(result.start["CRITICAL"], result.after_fixing["CRITICAL"], result.accepted["CRITICAL"]) == (2, 0, 0)`; `(result.start["HIGH"], result.after_fixing["HIGH"], result.accepted["HIGH"]) == (7, 2, 5)`; `result.meets_done_when`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_response.py` (lines 217 to 220):

```python
def test_a_critical_finding_left_open_fails_the_done_when():
    result = baseline([Finding("c", "t", "CRITICAL", "r")], [Finding("c", "t", "CRITICAL", "r")], [])
    assert result.unaccepted_critical == ("c",)
    assert not result.meets_done_when
```

A test: **a critical finding left open fails the done when**. Each `assert` line states what must be true: `result.unaccepted_critical == ("c",)`; `not result.meets_done_when`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_response.py` (lines 223 to 226):

```python
def test_an_acceptance_without_a_reason_does_not_count():
    result = baseline([], [Finding("c", "t", "CRITICAL", "r")], [Acceptance("c", "  ", "2026-10-22")])
    assert result.unaccepted_critical == ("c",)
    assert result.reasonless == ("c",)
```

A test: **an acceptance without a reason does not count**. Each `assert` line states what must be true: `result.unaccepted_critical == ("c",)`; `result.reasonless == ("c",)`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/unit/detect_respond/test_response.py` (lines 229 to 233):

```python
def test_posture_files_read_the_fixture_baseline():
    source = PostureFiles(Path("fixtures/posture"), Path("fixtures/posture/accepted.json"))
    result = posture_baseline(source, "before.json", "after.json")
    assert result.meets_done_when
    assert (result.start["CRITICAL"], result.after_fixing["HIGH"], result.accepted["HIGH"]) == (2, 2, 5)
```

A test: **posture files read the fixture baseline**. Each `assert` line states what must be true: `result.meets_done_when`; `(result.start["CRITICAL"], result.after_fixing["HIGH"], result.accepted["HIGH"]) == (2, 2, 5)`. If one is false the test fails and `pytest` shows both sides of the comparison.

#### `tests/e2e/test_pipeline.py`

From `tests/e2e/test_pipeline.py` (line 1):

```python
"""The lesson's drill and the offline pipeline, through `make`, as a reader runs them. Needs terraform and opa."""
```

The **docstring** of the module: a text in triple quotes at the very top of a file that says what the file is for. It does nothing when the program runs; tools and people read it as documentation.

From `tests/e2e/test_pipeline.py` (lines 3 to 5):

```python
import subprocess

import pytest
```

An **import** loads code from another file so it can be used here: `import x` loads the module `x`, and `from x import y` loads only the name `y` from it. The linter keeps imports in one order: standard library, then other libraries, then this project ([ruff.md](ruff.md)).

- `import subprocess`: makes the standard-library module `subprocess` (starts other programs) available; its contents are used as `subprocess.name`.
- `import pytest`: makes the library `pytest` (the test library) available; its contents are used as `pytest.name`.

From `tests/e2e/test_pipeline.py` (line 7):

```python
pytestmark = pytest.mark.e2e
```

`pytestmark = pytest.mark.e2e` labels every test in this file with the marker `e2e`; the default run skips marked tests and `make test-e2e` selects them ([pytest.md](pytest.md)).

From `tests/e2e/test_pipeline.py` (lines 10 to 12):

```python
def make(target: str) -> subprocess.CompletedProcess[str]:
    command = ["make", "--no-print-directory", target]
    return subprocess.run(command, capture_output=True, text=True, check=False, timeout=1200)
```

A helper that runs `make` with a target as a separate process (`subprocess.run`): `capture_output=True, text=True` collects the output as text, `check=False` means a failing exit code does not raise an error, and `timeout=1200` stops it after 20 minutes.

From `tests/e2e/test_pipeline.py` (lines 15 to 22):

```python
def test_both_environments_plan_validate_and_the_deployed_rules_equal_the_detection_files():
    result = make("validate")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "the plan deploys exactly the detections in detections/" in result.stdout
    assert "time to detect:  32 s" in result.stdout
    assert "time to contain: 6 min 52 s" in result.stdout
    assert "every logged file matches its digest" in result.stdout
    assert "is current" in result.stdout
```

A test: **both environments plan validate and the deployed rules equal the detection files**. Each `assert` line states what must be true: `result.returncode == 0, result.stdout + result.stderr`; `"the plan deploys exactly the detections in detections/" in result.stdout`; `"time to detect:  32 s" in result.stdout`; `"time to contain: 6 min 52 s" in result.stdout`; `"every logged file matches its digest" in result.stdout`; `"is current" in result.stdout`. If one is false the test fails and `pytest` shows both sides of the comparison.

From `tests/e2e/test_pipeline.py` (lines 25 to 29):

```python
def test_the_rehearsal_replay_on_its_own():
    result = make("demo-drill")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "6 alerts from detections: D1, D2, D4" in result.stdout
    assert "dry run, nothing changed" in result.stdout
```

A test: **the rehearsal replay on its own**. Each `assert` line states what must be true: `result.returncode == 0, result.stdout + result.stderr`; `"6 alerts from detections: D1, D2, D4" in result.stdout`; `"dry run, nothing changed" in result.stdout`. If one is false the test fails and `pytest` shows both sides of the comparison.

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
