"""Deterministic prompt instructions for producing schema-valid JSON."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, override

from xstructured.contracts import InstructionRenderer, require_instance
from xstructured.core.errors import SchemaError
from xstructured.envelope.spec import EnvelopeSpec

from ._resolve import resolve_schema, strip_annotations
from .introspection import SchemaInfo, SchemaTarget
from .named import NamedSchemas, NamedSchemaTargets
from .options import SchemaOptions

__all__ = ["DefaultInstructionRenderer", "schema_instructions"]

# Auto-generated titles add tokens without guiding the model; descriptions,
# defaults and examples are kept.
_DROPPED = frozenset({"title"})
_NO_EXTRAS = (
    "Put nothing else between the delimiters: no Markdown code fences, comments, or prose. "
    "Write any other text outside the block."
)


class DefaultInstructionRenderer(InstructionRenderer):
    """Render deterministic English instructions followed by the JSON Schema(s).

    Schema ``title`` keywords are dropped because they add tokens without guiding
    the model; descriptions, defaults, and examples are kept.
    """

    @override
    def render(
        self,
        schema: SchemaInfo | NamedSchemas | Mapping[str, Any],
        *,
        envelope: EnvelopeSpec | None,
        multiple: bool,
        multiple_envelopes: bool,
    ) -> str:
        if multiple_envelopes:
            if not isinstance(schema, NamedSchemas):
                raise SchemaError("multiple_envelopes requires named schemas")
            return _named_envelope_instructions(
                schema, envelope or EnvelopeSpec()
            )
        if isinstance(schema, NamedSchemas):
            value, schemas = _named_value(schema, multiple=multiple)
        else:
            document = (
                schema.json_schema if isinstance(schema, SchemaInfo) else schema
            )
            value = (
                "a JSON array whose items each validate against the JSON Schema below"
                if multiple
                else "a JSON value that validates against the JSON Schema below"
            )
            schemas = f"JSON Schema:\n{_json_block(document)}"
        if envelope is None:
            lead = (
                f"Respond with only {value}. Do not add Markdown code fences or any "
                "other text."
            )
        else:
            lead = (
                "Include exactly one structured block in your response, formatted as:\n\n"
                f"{envelope.start}JSON{envelope.end}\n\n"
                f"Replace JSON with {value}. {_NO_EXTRAS}"
            )
        return f"{lead}\n\n{schemas}"


def schema_instructions(
    target: SchemaTarget
    | SchemaInfo
    | NamedSchemaTargets
    | NamedSchemas
    | Mapping[str, Any],
    *,
    envelope: EnvelopeSpec | None = None,
    multiple: bool = False,
    multiple_envelopes: bool = False,
    options: SchemaOptions | None = None,
    renderer: InstructionRenderer | None = None,
) -> str:
    """Build deterministic instructions that ask a model for schema-valid JSON.

    Args:
        target: A schema target, a `SchemaInfo`, named schema targets, `NamedSchemas`,
            or a JSON Schema document.
        envelope: Ask for the JSON inside this envelope. Without an envelope the model is
            asked to respond with JSON only.
        multiple: Ask for a JSON array of values.
        multiple_envelopes: Ask for one named envelope per applicable named schema.
        options: Pydantic options used to generate the JSON Schema.
        renderer: Renders the instructions. Defaults to `DefaultInstructionRenderer`.

    Returns:
        Instructions followed by the JSON Schema(s) in fenced ``json`` blocks.

    Raises:
        ValueError: If both *multiple* and *multiple_envelopes* are set.
        TypeError: If *renderer* is not an `InstructionRenderer`.
        SchemaError: If *multiple_envelopes* is set without named schemas, or *target*
            cannot be introspected.
        EnvelopeError: If *multiple_envelopes* is set and the envelope is not tag-style.

    Example:
        ```python
        from pydantic import BaseModel
        from xstructured import EnvelopeSpec, schema_instructions


        class Contact(BaseModel):
            name: str
            email: str


        print(schema_instructions(Contact, envelope=EnvelopeSpec()))
        ```
    """
    if multiple and multiple_envelopes:
        raise ValueError(
            "multiple and multiple_envelopes are mutually exclusive"
        )
    active = (
        DefaultInstructionRenderer()
        if renderer is None
        else require_instance(renderer, InstructionRenderer, "renderer")
    )
    return active.render(
        resolve_schema(target, options=options),
        envelope=envelope,
        multiple=multiple,
        multiple_envelopes=multiple_envelopes,
    )


def _named_value(named: NamedSchemas, *, multiple: bool) -> tuple[str, str]:
    schema_key = named.spec.schema_key
    payload_key = named.spec.payload_key
    shape = f'{{"{schema_key}": "<name>", "{payload_key}": <value>}}'
    names = _quoted(named.names)
    if multiple:
        value = (
            f"a JSON array whose items are JSON objects of the form {shape}, where for each "
            f"item <name> is one of {names} and <value> validates against that name's "
            "JSON Schema below"
        )
    else:
        value = (
            f"a JSON object of the form {shape}, where <name> is one of {names} and "
            "<value> validates against that name's JSON Schema below"
        )
    return value, _named_blocks(named)


def _named_envelope_instructions(
    named: NamedSchemas, envelope: EnvelopeSpec
) -> str:
    return (
        "Include one structured block for each named schema below that applies to your "
        "response, formatted as:\n\n"
        f'{envelope.named_prefix}NAME">JSON{envelope.end}\n\n'
        f"Replace NAME with one of {_quoted(named.names)} (each name at most once) and JSON "
        f"with a JSON value that validates against that name's JSON Schema. {_NO_EXTRAS}"
        f"\n\n{_named_blocks(named)}"
    )


def _named_blocks(named: NamedSchemas) -> str:
    return "\n\n".join(
        f"JSON Schema for {json.dumps(name)}:\n{_json_block(named.schemas[name].json_schema)}"
        for name in named.names
    )


def _json_block(schema: Any) -> str:
    rendered = json.dumps(
        strip_annotations(schema, _DROPPED), ensure_ascii=False, indent=2
    )
    return f"```json\n{rendered}\n```"


def _quoted(names: tuple[str, ...]) -> str:
    return ", ".join(json.dumps(name) for name in names)
