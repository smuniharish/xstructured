"""Fingerprints depend only on validation semantics."""

from __future__ import annotations

from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from xstructured import fingerprint_schema

ANNOTATIONS = st.dictionaries(
    st.sampled_from(
        ["title", "description", "examples", "default", "$comment"]
    ),
    st.text(max_size=10),
)
TYPES = st.sampled_from(["string", "integer", "number", "boolean"])


@st.composite
def schemas(draw: st.DrawFn) -> tuple[dict[str, Any], dict[str, Any]]:
    """A JSON Schema and the same schema with random annotations and key order."""
    names = draw(
        st.lists(st.text(min_size=1, max_size=6), unique=True, max_size=5)
    )
    properties = {name: {"type": draw(TYPES)} for name in names}
    plain = {
        "type": "object",
        "properties": properties,
        "required": sorted(names),
    }
    annotated_properties = {
        name: {**draw(ANNOTATIONS), **schema}
        for name, schema in reversed(list(properties.items()))
    }
    annotated = {
        **draw(ANNOTATIONS),
        "required": sorted(names, reverse=True),
        "properties": annotated_properties,
        "type": "object",
    }
    return plain, annotated


@given(pair=schemas())
def test_annotations_and_ordering_do_not_matter(
    pair: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    plain, annotated = pair

    assert fingerprint_schema(plain) == fingerprint_schema(annotated)


@given(pair=schemas(), extra=st.text(min_size=1, max_size=6))
def test_adding_a_property_changes_the_fingerprint(
    pair: tuple[dict[str, Any], dict[str, Any]], extra: str
) -> None:
    plain, _ = pair
    if extra in plain["properties"]:
        return
    extended = {
        **plain,
        "properties": {**plain["properties"], extra: {"type": "string"}},
    }

    assert fingerprint_schema(extended) != fingerprint_schema(plain)
