# API reference

Everything is importable from `xstructured`.

## Wrapping Runnables

```text
with_xstructured_output(
    runnable, schema, *,
    envelope=None,              # EnvelopeSpec; default <xstructured>...</xstructured>
    parser_config=None,         # ParserConfig; an envelope is always required
    multiple=False,             # value is list[T]
    multiple_envelopes=False,   # value is dict[name, value]; needs named schemas
    inject_instructions=True,   # add instructions to str / PromptValue / message inputs
    repair=None,                # optional Runnable that corrects invalid responses
    repair_config=None,         # RepairConfig; only with repair=
) -> XStructuredRunnable[Input, T]
```

`XStructuredRunnable` properties: `runnable`, `parser`, `envelope`, `instructions`,
`schema_fingerprint`.

| Method | Returns |
| --- | --- |
| `invoke` / `ainvoke` | `XStructuredResult[T]` |
| `batch` / `abatch` | `list[XStructuredResult[T]]` |
| `stream` / `astream` | `StreamEvent[T]` values, ending with one `RESULT` |
| inside a composed chain | the final `XStructuredResult[T]` |

`XStructuredResult` fields: `content`, `structured`, `raw`, `raw_text`, `json_text`,
`recovered`, `schema_name`, `repaired`, `repair_attempts`, `metadata`.

`metadata` keys: `schema_fingerprint`, `envelope_count`, `parse_duration` (seconds), and
for message outputs `message_id`, `response_metadata`, `usage_metadata`.

## Parsing

```text
StructuredParser(schema, *, config=None, envelope=None, multiple=False, multiple_envelopes=False)
    .parse(text) -> ParseResult[T]          # full response
    .parse_payload(payload) -> ParseResult[T]  # JSON already taken out of its envelope
    .strip_envelopes(text) -> str           # prose only
```

`schema` is a model class, `TypeAdapter`, type annotation, `SchemaInfo`, a mapping of names
to schemas, or `NamedSchemas`. `ParseResult` fields: `value`, `raw`, `json_text`,
`recovered`, `envelope_spans`, `envelope_found`, `schema_name`, `repaired`,
`repair_attempts`.

## Envelopes and streaming

- `EnvelopeSpec(start="<xstructured>", end="</xstructured>")`: `wrap(payload, name=None)`,
  `named_start(name)`, `supports_names`. Delimiters cannot contain `"` or `\`.
- `EnvelopeScanner(spec, *, max_envelope_chars, max_payload_chars)`: `feed(chunk)` returns
  a `ScanEvent`; `finalize()`; `payload`, `span`, `complete`, `state`.
- `StreamDecoder(parser)`: `feed(chunk)` returns `list[StreamEvent]`; `finalize()`;
  `result`, `text`, `payload`.
- `StreamEventKind`: `TEXT_DELTA`, `STRUCTURED_START`, `STRUCTURED_DELTA`,
  `STRUCTURED_END`, `RESULT`.

## Schemas

- `inspect_schema(target) -> SchemaInfo` (`adapter`, `json_schema`, `name`,
  `validate_json`).
- `inspect_named_schemas(mapping, *, spec=NamedSchemaSpec()) -> NamedSchemas`.
- `schema_instructions(target, *, envelope=None, multiple=False, multiple_envelopes=False) -> str`.
- `fingerprint_schema(target, *, algorithm="sha256", include_metadata=False) -> str`.
- `canonical_schema_json(target, *, include_metadata=False) -> str`.

## Configuration and errors

- `ParserConfig`, `RecoveryConfig`, `RepairConfig`: see [configuration.md](configuration.md).
- `XStructuredError` > `SchemaError`, `EnvelopeError`, `ParseError` >
  `LimitExceededError`, `RecoveryError`, `RepairError`: see
  [troubleshooting.md](troubleshooting.md).
