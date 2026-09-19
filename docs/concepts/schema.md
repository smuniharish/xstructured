# Schema fingerprinting and instructions

`inspect_schema` builds a `pydantic.TypeAdapter` and JSON Schema for any
schema target -- a `BaseModel` subclass, a `TypeAdapter`, or any type
`TypeAdapter` accepts:

```python
from xstructured import inspect_schema

info = inspect_schema(ContactInfo)
info.validate_python({"name": "Priya Shah", "email": "priya.shah@example.com"})
```

## Instructions

`schema_instructions` turns that JSON Schema into a deterministic prompt
fragment, optionally naming an envelope:

```python
from xstructured import schema_instructions

print(schema_instructions(ContactInfo, envelope="xstructured"))
```

The output is a short prefix ("Return the JSON value inside the
`xstructured` envelope:") followed by the schema's JSON Schema in a fenced
```json``` block, ready to append to a system or user prompt.

## Fingerprinting

`fingerprint_schema` hashes a canonical, key-sorted serialization of the
JSON Schema (with non-semantic keys like `title` and `description` excluded
by default), so two schemas that only differ in documentation strings
fingerprint identically, while any change to required fields, types, or
constraints changes the hash:

```python
from xstructured import fingerprint_schema

digest = fingerprint_schema(ContactInfo)
```

`XStructuredRunnable.schema_fingerprint` exposes this on every wrapped
Runnable, and it is included in `XStructuredResult.metadata["schema_fingerprint"]`
on every result -- useful for cache keys, telemetry, and detecting when a
schema has drifted between a prompt and a stored result.

## Named schemas

Sometimes a single response could validly be one of several different
shapes -- for example a support-ticket handler that produces either a
`Contact` or a `Ticket` object. `inspect_schema`, `schema_instructions`, and
`fingerprint_schema` all accept a **mapping of names to schema targets** (or
a pre-built `NamedSchemas`) as an alternative to a single schema target:

```python
from xstructured import StructuredParser, inspect_named_schemas, schema_instructions

named = inspect_named_schemas({"contact": ContactInfo, "ticket": TicketInfo})
print(schema_instructions(named, envelope="xstructured"))

parser = StructuredParser({"contact": ContactInfo, "ticket": TicketInfo})
result = parser.parse(model_output)
print(result.schema_name)  # "contact" or "ticket"
```

The model is instructed to return exactly one JSON object of the form
`{"schema": "<name>", "payload": <value>}`, where `<name>` is one of the
configured keys and `<value>` validates against that name's schema. This is
still a **single-result contract** (see
[Multiple payloads](multiple-payloads.md)): named schemas let one response
choose *which* schema applies, they do not let a response contain more than
one payload.

`ParseResult.schema_name` and `XStructuredResult.schema_name` report which
named schema matched; both are `None` for the single-schema case, preserving
existing behavior and result shapes. An unrecognized `"schema"` name, or a
missing `"schema"`/`"payload"` key, is treated like any other schema-invalid
input and raises `RecoveryError` (or `RepairError` when a repair Runnable is
configured -- see [Repair and recovery](repair.md)).

The discriminator and payload key names default to `"schema"` and
`"payload"` and can be customized with `NamedSchemaSpec`:

```python
from xstructured import NamedSchemaSpec, NamedSchemas, inspect_named_schemas

named = inspect_named_schemas(
    {"contact": ContactInfo, "ticket": TicketInfo},
    spec=NamedSchemaSpec(schema_key="kind", payload_key="data"),
)
```
