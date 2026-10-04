"""Strict, bounded JSON decoding."""

from __future__ import annotations

import json
import math
from typing import Any

from xstructured._scan import nesting_exceeds

__all__ = ["JsonSafetyError", "loads_strict"]


class JsonSafetyError(ValueError):
    """JSON text violates a safety rule."""


def loads_strict(text: str, *, max_nesting_depth: int) -> Any:
    """Decode standard JSON, rejecting unsafe or ambiguous documents.

    Rejected: nesting deeper than *max_nesting_depth*, duplicate object keys, the
    non-standard constants ``NaN``, ``Infinity`` and ``-Infinity``, and numbers that
    overflow to an infinite float.

    Raises:
        JsonSafetyError: If a safety rule is violated.
        json.JSONDecodeError: If *text* is not valid JSON.
    """
    if nesting_exceeds(text, max_nesting_depth):
        raise JsonSafetyError(
            f"JSON nesting exceeds the configured limit of {max_nesting_depth}"
        )
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
            parse_float=_parse_finite_float,
        )
    except RecursionError as exc:
        raise JsonSafetyError("JSON nesting is too deep to decode") from exc


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise JsonSafetyError(f"Duplicate JSON object key {key!r}")
        result[key] = value
    return result


def _reject_constant(name: str) -> None:
    raise JsonSafetyError(f"Non-standard JSON constant {name!r}")


def _parse_finite_float(text: str) -> float:
    value = float(text)
    if math.isinf(value):
        raise JsonSafetyError(f"JSON number {text!r} overflows a float")
    return value
