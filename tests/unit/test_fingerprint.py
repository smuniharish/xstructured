from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import BaseModel, Field

from tests.support import Answer, Label
from xstructured import (
    canonical_schema_json,
    fingerprint_schema,
    inspect_named_schemas,
    inspect_schema,
)


class WithTitle(BaseModel):
    title: str
    body: str


class WithoutTitle(BaseModel):
    body: str


class Documented(BaseModel):
    """Documented."""

    value: int = Field(description="A value.", examples=[1])


def test_annotations_do_not_change_the_fingerprint() -> None:
    first = {"type": "object", "title": "One", "description": "first"}
    second = {"description": "second", "title": "Two", "type": "object"}

    assert fingerprint_schema(first) == fingerprint_schema(second)
    assert fingerprint_schema(
        first, include_metadata=True
    ) != fingerprint_schema(second, include_metadata=True)
    assert fingerprint_schema(Documented) == fingerprint_schema(Answer)


def test_fields_named_like_annotations_are_part_of_the_fingerprint() -> None:
    assert fingerprint_schema(WithTitle) != fingerprint_schema(WithoutTitle)


def test_semantic_changes_change_the_fingerprint() -> None:
    assert fingerprint_schema(Answer) != fingerprint_schema(Label)
    assert fingerprint_schema({"type": "integer"}) != fingerprint_schema(
        {"type": "number"}
    )


@pytest.mark.parametrize(
    "document",
    [
        {},
        {"enum": ["a", "b"]},
        {"$ref": "#/$defs/A"},
        {"const": {"title": "data"}},
    ],
)
def test_any_json_schema_document_can_be_fingerprinted(
    document: dict[str, object],
) -> None:
    canonical = json.loads(canonical_schema_json(document))

    assert canonical == document
    assert len(fingerprint_schema(document)) == 64


def test_canonical_json_is_compact_sorted_and_ascii() -> None:
    assert canonical_schema_json({"b": 1, "a": "é"}) == '{"a":"\\u00e9","b":1}'


def test_schema_targets_and_schema_infos_share_a_fingerprint() -> None:
    assert fingerprint_schema(Answer) == fingerprint_schema(
        inspect_schema(Answer)
    )


def test_named_fingerprints_are_order_independent_and_distinct() -> None:
    both = fingerprint_schema({"answer": Answer, "label": Label})

    assert both == fingerprint_schema(
        inspect_named_schemas({"label": Label, "answer": Answer})
    )
    assert both != fingerprint_schema({"answer": Answer})
    assert fingerprint_schema({"answer": Answer}) != fingerprint_schema(Answer)


def test_alternative_algorithms() -> None:
    expected = hashlib.sha512(
        canonical_schema_json(Answer).encode()
    ).hexdigest()

    assert fingerprint_schema(Answer, algorithm="sha512") == expected


@pytest.mark.parametrize(
    ("algorithm", "message"),
    [("not-an-algorithm", "Unsupported"), ("shake_256", "Variable-length")],
)
def test_unsupported_algorithms_are_rejected(
    algorithm: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        fingerprint_schema(Answer, algorithm=algorithm)
