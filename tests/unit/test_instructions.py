from __future__ import annotations

import json
import re

import pytest
from pydantic import BaseModel, Field

from tests.support import Answer, Label
from xstructured import (
    EnvelopeError,
    EnvelopeSpec,
    NamedSchemaSpec,
    SchemaError,
    inspect_named_schemas,
    inspect_schema,
    schema_instructions,
)


class Document(BaseModel):
    """A model with a field literally named ``title``."""

    title: str = Field(description="Shown to readers.")


def schema_blocks(instructions: str) -> list[object]:
    return [
        json.loads(block)
        for block in re.findall(r"```json\n(.*?)\n```", instructions, re.DOTALL)
    ]


def test_plain_instructions_ask_for_json_only() -> None:
    instructions = schema_instructions(Answer)

    assert instructions.startswith(
        "Respond with only a JSON value that validates against the JSON Schema below."
    )
    assert schema_blocks(instructions) == [
        {
            "properties": {"value": {"type": "integer"}},
            "required": ["value"],
            "type": "object",
        }
    ]


def test_envelope_instructions_show_the_exact_delimiters() -> None:
    instructions = schema_instructions(
        Answer, envelope=EnvelopeSpec("<result>", "</result>")
    )

    assert "<result>JSON</result>" in instructions
    assert "Put nothing else between the delimiters" in instructions


def test_multiple_instructions_ask_for_an_array() -> None:
    assert "a JSON array whose items each validate" in schema_instructions(
        Answer, multiple=True
    )


def test_titles_are_dropped_but_fields_named_title_and_descriptions_are_kept() -> (
    None
):
    [block] = schema_blocks(schema_instructions(Document))

    assert block == {
        "description": "A model with a field literally named ``title``.",
        "properties": {
            "title": {"description": "Shown to readers.", "type": "string"}
        },
        "required": ["title"],
        "type": "object",
    }


def test_named_instructions_describe_the_discriminated_shape() -> None:
    instructions = schema_instructions(
        inspect_named_schemas(
            {"label": Label, "answer": Answer},
            spec=NamedSchemaSpec(schema_key="kind", payload_key="data"),
        ),
        envelope=EnvelopeSpec(),
    )

    assert '{"kind": "<name>", "data": <value>}' in instructions
    assert '<name> is one of "answer", "label"' in instructions
    assert instructions.index('JSON Schema for "answer"') < instructions.index(
        'JSON Schema for "label"'
    )
    assert len(schema_blocks(instructions)) == 2


def test_named_array_instructions() -> None:
    instructions = schema_instructions(
        {"answer": Answer, "label": Label}, multiple=True
    )

    assert (
        "a JSON array whose items are JSON objects of the form" in instructions
    )


def test_named_envelope_instructions() -> None:
    instructions = schema_instructions(
        {"answer": Answer, "label": Label},
        envelope=EnvelopeSpec("<r>", "</r>"),
        multiple_envelopes=True,
    )

    assert '<r name="NAME">JSON</r>' in instructions
    assert (
        'Replace NAME with one of "answer", "label" (each name at most once)'
        in instructions
    )


def test_named_envelope_instructions_default_to_the_standard_envelope() -> None:
    instructions = schema_instructions(
        {"answer": Answer}, multiple_envelopes=True
    )

    assert '<xstructured name="NAME">JSON</xstructured>' in instructions


def test_json_schema_documents_and_schema_infos_are_accepted() -> None:
    assert schema_blocks(
        schema_instructions({"type": "string", "title": "T"})
    ) == [{"type": "string"}]
    assert schema_instructions(inspect_schema(Answer)) == schema_instructions(
        Answer
    )


def test_instructions_are_deterministic() -> None:
    assert schema_instructions(
        {"b": Label, "a": Answer}
    ) == schema_instructions({"a": Answer, "b": Label})


def test_invalid_combinations_are_rejected() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        schema_instructions(
            {"a": Answer}, multiple=True, multiple_envelopes=True
        )
    with pytest.raises(SchemaError, match="requires named schemas"):
        schema_instructions(Answer, multiple_envelopes=True)
    with pytest.raises(EnvelopeError, match="tag-style"):
        schema_instructions(
            {"a": Answer},
            envelope=EnvelopeSpec("[[", "]]"),
            multiple_envelopes=True,
        )
