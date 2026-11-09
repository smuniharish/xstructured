"""A JSON decoder and a recovery strategy to copy into a project.

`PythonLiteralDecoder` accepts standard JSON first, then Python literals such
as single-quoted strings and `True`, which some models emit. It keeps every
safety rule of `StrictJsonDecoder`: nesting limits, duplicate keys, `NaN`.

`LastLineFirst` tries the response's last line before the default candidates,
for models that put the JSON on its own final line.

Adapt both, keep the rules in the comments, and run `test_extensions.py`.
"""

from __future__ import annotations

import ast
import json
from typing import Any, override

from xstructured import (
    ConservativeRecovery,
    JsonDecoder,
    JsonSafetyError,
    RecoveryStrategy,
    StrictJsonDecoder,
)


class PythonLiteralDecoder(JsonDecoder):
    """Decode standard JSON, falling back to Python literals."""

    def __init__(self) -> None:
        self._strict = StrictJsonDecoder()

    @override
    def decode(self, text: str, *, max_nesting_depth: int) -> Any:
        try:
            return self._strict.decode(
                text, max_nesting_depth=max_nesting_depth
            )
        except JsonSafetyError:
            # Too deep, duplicate keys, or NaN: never fall back to a looser decoder.
            raise
        except ValueError:
            pass
        try:
            value = ast.literal_eval(text)
            # Only values that have a JSON form: no sets, bytes, or NaN.
            json.dumps(value, allow_nan=False)
        except (
            SyntaxError,
            TypeError,
            ValueError,
            MemoryError,
            RecursionError,
        ) as error:
            # Every rejection must be a ValueError so the parser tries the next candidate.
            raise ValueError(
                f"not JSON or a Python literal: {error}"
            ) from error
        return value

    # json_text is inherited: it serializes the decoded value to standard JSON,
    # which Pydantic then validates in JSON mode.


class LastLineFirst(RecoveryStrategy):
    """Try the stripped text, then its last line, then the default candidates."""

    def __init__(self) -> None:
        self._default = ConservativeRecovery()

    @override
    def candidates(self, text: str) -> list[str]:
        stripped = text.strip()
        last = stripped.splitlines()[-1].strip() if stripped else ""
        found = [stripped, last, *self._default.candidates(text)]
        # The first candidate is the stripped text; every candidate is a
        # non-empty substring of the text, and none repeats.
        return [candidate for candidate in dict.fromkeys(found) if candidate]
