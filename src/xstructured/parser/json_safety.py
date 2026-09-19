"""Bounded strict JSON decoding helpers."""

from __future__ import annotations

import json
from typing import Any


class JsonSafetyError(ValueError):
    """Raised when JSON exceeds a configured safety constraint."""


def loads_strict(text: str, *, max_nesting_depth: int) -> Any:
    """Decode standard JSON after rejecting excessive container nesting."""
    _validate_nesting_depth(text, max_nesting_depth)
    return json.loads(
        text,
        parse_constant=_reject_non_standard_constant,
        object_pairs_hook=_reject_duplicate_keys,
    )


def _validate_nesting_depth(text: str, max_nesting_depth: int) -> None:
    depth = 0
    in_string = False
    escaped = False

    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > max_nesting_depth:
                raise JsonSafetyError(
                    f"JSON nesting exceeds configured limit of {max_nesting_depth}"
                )
        elif character in "]}":
            depth -= 1


def _reject_non_standard_constant(value: str) -> None:
    raise JsonSafetyError(f"Non-standard JSON constant {value!r} is not permitted")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise JsonSafetyError(f"Duplicate JSON object key {key!r} is not permitted")
        result[key] = value
    return result
