from typing import Literal

from pydantic import BaseModel, Field

from xstructured.schema import fingerprint_schema, inspect_schema, schema_instructions


class Ticket(BaseModel):
    priority: Literal["low", "high"]
    title: str = Field(min_length=3)


def test_introspection_validates_and_exposes_json_schema() -> None:
    schema = inspect_schema(Ticket)

    assert schema.name == "Ticket"
    assert schema.validate_python({"priority": "high", "title": "Fix"}) == Ticket(
        priority="high", title="Fix"
    )
    assert schema.json_schema["properties"]["priority"]["enum"] == ["low", "high"]


def test_fingerprint_ignores_presentation_metadata() -> None:
    first = {"type": "object", "title": "One", "description": "first"}
    second = {"description": "second", "title": "Two", "type": "object"}

    assert fingerprint_schema(first) == fingerprint_schema(second)
    assert fingerprint_schema(first, include_metadata=True) != fingerprint_schema(
        second, include_metadata=True
    )


def test_instructions_include_schema_and_optional_envelope() -> None:
    instructions = schema_instructions(Ticket, envelope="result")

    assert "inside the `result` envelope" in instructions
    assert '"priority"' in instructions
