"""Properties of envelope extraction, parsing, and recovery."""

from __future__ import annotations

import json
import math
from typing import Any, Literal

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from pydantic import BaseModel, Field, TypeAdapter

from tests.support import chunked
from xstructured import (
    EnvelopeScanner,
    EnvelopeSpec,
    ParseError,
    StructuredParser,
)
from xstructured.parser.json_safety import JsonSafetyError, loads_strict

JSON_SCALARS = (
    st.none()
    | st.booleans()
    | st.integers(min_value=-(10**12), max_value=10**12)
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=20)
)
JSON_VALUES = st.recursive(
    JSON_SCALARS,
    lambda children: (
        st.lists(children, max_size=4)
        | st.dictionaries(st.text(max_size=8), children, max_size=4)
    ),
    max_leaves=20,
)
PROSE = st.text(max_size=40).filter(lambda text: "<xstructured>" not in text)
WIDTHS = st.lists(st.integers(min_value=1, max_value=9), max_size=30)


class Inner(BaseModel):
    tag: Literal["a", "b"]
    weight: float = Field(allow_inf_nan=False)


class Record(BaseModel):
    name: str
    count: int
    flags: list[bool]
    inner: Inner | None = None
    notes: dict[str, str] = Field(default_factory=dict)


RECORDS = st.builds(
    Record,
    name=st.text(max_size=20),
    count=st.integers(),
    flags=st.lists(st.booleans(), max_size=5),
    inner=st.none()
    | st.builds(
        Inner,
        tag=st.sampled_from(["a", "b"]),
        weight=st.floats(allow_nan=False, allow_infinity=False),
    ),
    notes=st.dictionaries(
        st.text(max_size=5), st.text(max_size=10), max_size=3
    ),
)


@given(value=JSON_VALUES)
def test_strict_decoding_round_trips_standard_json(value: Any) -> None:
    assert loads_strict(json.dumps(value), max_nesting_depth=1_000) == value


@given(key=st.text(max_size=5), first=JSON_SCALARS, second=JSON_SCALARS)
def test_duplicate_keys_are_always_rejected(
    key: str, first: Any, second: Any
) -> None:
    name = json.dumps(key)
    document = f"{{{name}: {json.dumps(first)}, {name}: {json.dumps(second)}}}"

    with pytest.raises(JsonSafetyError, match="Duplicate"):
        loads_strict(document, max_nesting_depth=10)


@given(
    record=RECORDS,
    prose=PROSE,
    wrapper=st.sampled_from(["bare", "fence", "prose"]),
)
def test_models_round_trip_through_common_response_shapes(
    record: Record, prose: str, wrapper: str
) -> None:
    payload = record.model_dump_json()
    text = {
        "bare": payload,
        "fence": f"```json\n{payload}\n```",
        "prose": f"Here you go:\n{payload}\nThanks!",
    }[wrapper]

    result = StructuredParser(Record).parse(text)

    assert result.value == record
    assert result.recovered is (wrapper != "bare")
    assert json.loads(result.json_text) == json.loads(payload)


@given(text=st.text(alphabet='{}[]"ab:1, \n`', max_size=40))
def test_recovery_never_invents_json(text: str) -> None:
    try:
        result = StructuredParser(TypeAdapter(Any)).parse(text)
    except ParseError:
        return

    assert result.json_text in text


@given(record=RECORDS, before=PROSE, after=st.text(max_size=40), widths=WIDTHS)
def test_envelopes_are_extracted_at_any_chunk_boundaries(
    record: Record, before: str, after: str, widths: list[int]
) -> None:
    payload = record.model_dump_json()
    envelope = EnvelopeSpec()
    text = before + envelope.wrap(payload) + after
    scanner = EnvelopeScanner(envelope)
    outside: list[str] = []
    for chunk in chunked(text, widths):
        event = scanner.feed(chunk)
        outside.extend((event.text_before, event.text_after))

    assert scanner.payload == payload
    assert "".join(outside) == before + after
    assert scanner.span == (
        len(before),
        len(before) + len(envelope.wrap(payload)),
    )
    assert (
        StructuredParser(Record, envelope=envelope).parse(text).value == record
    )


@given(value=st.floats(allow_nan=False, allow_infinity=False))
def test_finite_floats_are_preserved_exactly(value: float) -> None:
    assume(math.isfinite(value))

    assert loads_strict(json.dumps(value), max_nesting_depth=1) == value
