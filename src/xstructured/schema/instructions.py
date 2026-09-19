"""Human-readable JSON Schema instructions for model prompts."""

from __future__ import annotations

import json
from typing import Any

from .introspection import SchemaTarget, inspect_schema
from .named import NamedSchemas


def schema_instructions(
    target: SchemaTarget | dict[str, Any] | NamedSchemas,
    *,
    envelope: str | None = None,
    multiple: bool = False,
    multiple_envelopes: bool = False,
) -> str:
    """Create concise, deterministic instructions for producing schema-valid JSON."""
    if isinstance(target, NamedSchemas):
        return _named_schema_instructions(
            target, envelope=envelope, multiple=multiple, multiple_envelopes=multiple_envelopes
        )
    schema = target if isinstance(target, dict) else inspect_schema(target).json_schema
    serialized = json.dumps(schema, ensure_ascii=True, indent=2, sort_keys=True)
    prefix = "Return only a JSON value that validates against this JSON Schema:"
    if multiple:
        prefix = "Return only a JSON array whose items validate against this JSON Schema:"
    if envelope is not None:
        value = "JSON array" if multiple else "JSON value"
        prefix = f"Return the {value} inside the `{envelope}` envelope:"
    return f"{prefix}\n\n```json\n{serialized}\n```"


def _named_schema_instructions(
    named: NamedSchemas, *, envelope: str | None, multiple: bool, multiple_envelopes: bool
) -> str:
    spec = named.spec
    names = sorted(named.schemas)
    blocks = [
        f'Schema "{name}":\n```json\n'
        f"{
            json.dumps(
                named.schemas[name].json_schema,
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
        }"
        "\n```"
        for name in names
    ]
    item_shape = (
        f'{{"{spec.schema_key}": "<name>", "{spec.payload_key}": <value>}}'
    )
    if multiple_envelopes:
        return (
            "Return one separately named envelope for every applicable schema. "
            "Use exactly `<xstructured name=\"name\">JSON</xstructured>` with "
            f"name values from {names}. Validate each JSON value against its schema."
            + "\n\n"
            + "\n\n".join(blocks)
        )
    shape = (
        f"Return a JSON array of items shaped {item_shape}, "
        if multiple
        else "Return exactly one JSON object of the form "
        f"{item_shape}, "
    ) + (
        f'where "<name>" is exactly one of {names} and <value> validates against '
        "that name's JSON Schema below."
    )
    prefix = shape
    if envelope is not None:
        value = "JSON array" if multiple else "JSON value"
        prefix = f"Return the {value} inside the `{envelope}` envelope. {shape}"
    return f"{prefix}\n\n" + "\n\n".join(blocks)
