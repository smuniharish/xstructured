from __future__ import annotations

import json

import pytest

from xstructured.parser.json_safety import JsonSafetyError, loads_strict


def test_decodes_standard_json() -> None:
    assert loads_strict(
        '{"a": [1, 2.5, "x", null, true]}', max_nesting_depth=5
    ) == {"a": [1, 2.5, "x", None, True]}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ('{"a": 1, "a": 2}', "Duplicate JSON object key"),
        ('{"a": NaN}', "Non-standard JSON constant"),
        ('{"a": Infinity}', "Non-standard JSON constant"),
        ('{"a": -Infinity}', "Non-standard JSON constant"),
        ('{"a": 1e400}', "overflows a float"),
        ('{"a": -1e400}', "overflows a float"),
        ("[[[1]]]", "nesting exceeds"),
    ],
)
def test_rejects_unsafe_documents(text: str, message: str) -> None:
    with pytest.raises(JsonSafetyError, match=message):
        loads_strict(text, max_nesting_depth=2)


def test_invalid_json_raises_a_decode_error() -> None:
    with pytest.raises(json.JSONDecodeError):
        loads_strict("{", max_nesting_depth=5)


def test_decoder_recursion_is_reported_as_a_safety_error() -> None:
    depth = 200_000
    with pytest.raises(JsonSafetyError, match="too deep"):
        loads_strict("[" * depth + "]" * depth, max_nesting_depth=depth)
