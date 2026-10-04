<!-- docs-test: run -->

# Schemas and instructions

## Schema targets

Anything Pydantic v2 can validate works as a schema: a `BaseModel` subclass, a
`TypeAdapter`, or a type annotation such as `list[int]` or `Literal["low", "high"]`.
`inspect_schema` resolves a target once into a `SchemaInfo` holding the adapter, the JSON
Schema, and a display name; the parser and wrapper do this for you.

```python
from typing import Literal

from pydantic import BaseModel, Field

from xstructured import inspect_schema


class Ticket(BaseModel):
    """A support ticket."""

    title: str = Field(description="One-line summary.")
    priority: Literal["low", "high"]


info = inspect_schema(Ticket)
assert info.name == "Ticket"
assert info.json_schema["properties"]["priority"]["enum"] == ["low", "high"]
```

## Instructions

`schema_instructions` builds deterministic prompt text that tells a model exactly what to
produce. With an envelope, it shows the literal delimiters to use:

```python
from xstructured import EnvelopeSpec, schema_instructions

print(schema_instructions(Ticket, envelope=EnvelopeSpec()))
```

````text
Include exactly one structured block in your response, formatted as:

<xstructured>JSON</xstructured>

Replace JSON with a JSON value that validates against the JSON Schema below. Put nothing else between the delimiters: no Markdown code fences, comments, or prose. Write any other text outside the block.

JSON Schema:
```json
{
  "description": "A support ticket.",
  "properties": {
    "title": {
      "description": "One-line summary.",
      "type": "string"
    },
    "priority": {
      "enum": [
        "low",
        "high"
      ],
      "type": "string"
    }
  },
  "required": [
    "title",
    "priority"
  ],
  "type": "object"
}
```
````

Field order is preserved, descriptions and examples are kept to guide the model, and
auto-generated titles are omitted to save tokens. `with_xstructured_output` adds these
instructions to every input; its `instructions` property returns the same text for use in
your own prompts.

## Named schemas

When a response may legitimately take one of several shapes, give each schema a name.
The model then answers with `{"schema": "<name>", "payload": <value>}` and
`ParseResult.schema_name` tells you which schema matched:

```python
from xstructured import StructuredParser


class Refund(BaseModel):
    order_id: str
    amount: float


parser = StructuredParser({"ticket": Ticket, "refund": Refund})
result = parser.parse(
    '{"schema": "refund", "payload": {"order_id": "A-17", "amount": 25.0}}'
)

assert result.value == Refund(order_id="A-17", amount=25.0)
assert result.schema_name == "refund"
```

`NamedSchemaSpec` changes the discriminator and payload keys, and `inspect_named_schemas`
resolves a reusable `NamedSchemas` value:

```python
from xstructured import NamedSchemaSpec, inspect_named_schemas

named = inspect_named_schemas(
    {"ticket": Ticket, "refund": Refund},
    spec=NamedSchemaSpec(schema_key="kind", payload_key="data"),
)
result = StructuredParser(named).parse(
    '{"kind": "ticket", "data": {"title": "Login fails", "priority": "high"}}'
)
assert result.schema_name == "ticket"
```

## Fingerprints

`fingerprint_schema` hashes a canonical form of the JSON Schema. Annotations such as
titles, descriptions, defaults, and examples are excluded, and `required` lists are
treated as sets, so documentation edits keep the fingerprint while any change to types,
constraints, or required fields changes it. Use it for cache keys, telemetry, and drift
detection.

```python
from xstructured import fingerprint_schema


class TicketV2(BaseModel):
    """Reworded documentation only."""

    title: str = Field(description="Short summary of the problem.")
    priority: Literal["low", "high"]


class TicketV3(BaseModel):
    title: str
    priority: Literal["low", "medium", "high"]


assert fingerprint_schema(Ticket) == fingerprint_schema(TicketV2)
assert fingerprint_schema(Ticket) != fingerprint_schema(TicketV3)
```

`fingerprint_schema` and `schema_instructions` also accept raw JSON Schema documents and
named schemas. `canonical_schema_json` returns the exact text that is hashed.
