from __future__ import annotations

from typing import Literal

import pytest
from pydantic import BaseModel, Field, TypeAdapter

from tests.support import Answer, Label
from xstructured import (
    NamedSchemas,
    NamedSchemaSpec,
    SchemaError,
    SchemaInfo,
    inspect_named_schemas,
    inspect_schema,
)
from xstructured.schema._resolve import (
    is_named_targets,
    resolve_schema,
    strip_annotations,
)


class Ticket(BaseModel):
    priority: Literal["low", "high"]
    title: str = Field(min_length=3)


def test_inspect_schema_builds_an_adapter_and_json_schema() -> None:
    info = inspect_schema(Ticket)

    assert info.target is Ticket
    assert info.name == "Ticket"
    assert info.json_schema["properties"]["priority"]["enum"] == ["low", "high"]
    assert info.validate_json('{"priority": "high", "title": "Fix"}') == Ticket(
        priority="high", title="Fix"
    )


def test_inspect_schema_accepts_adapters_annotations_and_schema_infos() -> None:
    adapter = TypeAdapter(list[int])
    info = inspect_schema(adapter)

    assert info.adapter is adapter
    assert inspect_schema(info) is info
    assert inspect_schema(int).name == "int"
    assert inspect_schema(list[int]).name == "list"
    assert inspect_schema(TypeAdapter(int)).name == "structured output"


@pytest.mark.parametrize(
    "target", [object(), "NotAType", "#/not/a/python/expression"]
)
def test_inspect_schema_reports_unsupported_targets(target: object) -> None:
    with pytest.raises(SchemaError, match="Cannot introspect"):
        inspect_schema(target)


def test_named_schemas_are_resolved_and_immutable() -> None:
    named = inspect_named_schemas({"ticket": Ticket, "answer": Answer})

    assert named.names == ("answer", "ticket")
    assert named.resolve("ticket").name == "Ticket"
    assert hash(named) == hash(named)
    with pytest.raises(TypeError):
        named.schemas["other"] = inspect_schema(Label)  # type: ignore[index]
    with pytest.raises(
        SchemaError, match="not one of the configured schema names"
    ):
        named.resolve("missing")


def test_inspect_named_schemas_reuses_or_respecs_existing_named_schemas() -> (
    None
):
    named = inspect_named_schemas({"answer": Answer})
    spec = NamedSchemaSpec(schema_key="kind", payload_key="data")

    assert inspect_named_schemas(named) is named
    respecced = inspect_named_schemas(named, spec=spec)
    assert respecced.spec == spec
    assert respecced.schemas == named.schemas


@pytest.mark.parametrize("name", ["", "has space", "x" * 65, 3])
def test_named_schema_names_are_validated(name: object) -> None:
    with pytest.raises(SchemaError, match="Invalid schema name"):
        NamedSchemas({name: inspect_schema(Answer)})  # type: ignore[dict-item]


def test_at_least_one_named_schema_is_required() -> None:
    with pytest.raises(SchemaError, match="At least one"):
        inspect_named_schemas({})


@pytest.mark.parametrize(
    ("schema_key", "payload_key"), [("", "payload"), ("same", "same")]
)
def test_named_schema_spec_validation(
    schema_key: str, payload_key: str
) -> None:
    with pytest.raises(SchemaError):
        NamedSchemaSpec(schema_key=schema_key, payload_key=payload_key)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ({"a": Answer, "b": TypeAdapter(int)}, True),
        ({"a": list[int], "b": Literal["x"]}, True),
        ({}, False),
        ({"type": "object"}, False),
        ({"enum": ["a", "b"]}, False),
        ({"$ref": "#/$defs/A"}, False),
        ({"a": Answer, "b": None}, False),
        (Answer, False),
    ],
)
def test_named_targets_are_told_apart_from_json_schema(
    value: object, expected: bool
) -> None:
    assert is_named_targets(value) is expected


def test_resolve_schema_classifies_every_input() -> None:
    info = inspect_schema(Answer)
    named = inspect_named_schemas({"a": Answer})

    assert resolve_schema(info) is info
    assert resolve_schema(named) is named
    assert isinstance(resolve_schema(Answer), SchemaInfo)
    assert isinstance(resolve_schema({"a": Answer}), NamedSchemas)
    assert resolve_schema({"type": "string"}) == {"type": "string"}


def test_strip_annotations_only_touches_schema_keywords() -> None:
    schema = {
        "title": "Doc",
        "type": "object",
        "properties": {
            "title": {"title": "Title", "type": "string"},
            "items": {
                "type": "array",
                "items": {"title": "Item", "type": "integer"},
            },
            "pair": {"prefixItems": [{"title": "First"}], "items": False},
        },
        "$defs": {"Inner": {"title": "Inner", "not": {"title": "No"}}},
        "anyOf": [{"title": "A"}, True],
        "enum": [{"title": "kept"}],
        "required": ["title"],
    }

    assert strip_annotations(schema, frozenset({"title"})) == {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "items": {"type": "array", "items": {"type": "integer"}},
            "pair": {"prefixItems": [{}], "items": False},
        },
        "$defs": {"Inner": {"not": {}}},
        "anyOf": [{}, True],
        "enum": [{"title": "kept"}],
        "required": ["title"],
    }
