"""The EventBridge event-pattern language, as far as the detections use it: exact values, `anything-but`, `prefix`,
`suffix`, `exists`, nested objects and `$or`. Anything else raises instead of silently never matching."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from detect_respond.domain.errors import UnsupportedPatternError

_OPERATORS = {"anything-but", "prefix", "suffix", "exists"}


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


def _leaf_matches(alternatives: list[Any], value: Any, present: bool) -> bool:
    values = value if isinstance(value, list) else [value]
    return any(_alternative_matches(alternative, values, present) for alternative in alternatives)


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
