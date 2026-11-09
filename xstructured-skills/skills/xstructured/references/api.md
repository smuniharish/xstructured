# API

Everything below is importable from `xstructured`, except
`XStructuredMiddleware` (`xstructured.agents`), `OpenTelemetryObserver`
(`xstructured.otel`), and the test helpers (`xstructured.testing`).

## Attach points

```text
with_xstructured_output(
    runnable, schema, *, envelope=None, parser_config=None, multiple=False,
    multiple_envelopes=False, inject_instructions=True, repair=None,
    repair_config=None, schema_options=None, renderer=None, injector=None,
    extractor=None, recovery=None, decoder=None, repair_prompt=None,
    observer=None, name=None,
) -> XStructuredRunnable

XStructuredMiddleware(
    schema, *, envelope=None, parser_config=None, multiple=False,
    multiple_envelopes=False, inject_instructions=True, repair_config=None,
    schema_options=None, renderer=None, extractor=None, recovery=None,
    decoder=None, repair_prompt=None, observer=None, name=None,
)

XStructuredOutputParser(
    schema, *, envelope=None, parser_config=None, multiple=False,
    multiple_envelopes=False, schema_options=None, renderer=None,
    recovery=None, decoder=None,
)

StructuredParser(
    schema, *, config=None, envelope=None, multiple=False,
    multiple_envelopes=False, schema_options=None, recovery=None,
    decoder=None,
)
```

- `schema`: a Pydantic model, a `TypeAdapter`, any annotation Pydantic
  accepts (`list[Item]`, a `TypedDict`, a union), or a mapping of names to
  schemas for named payloads.
- `XStructuredRunnable` exposes `runnable`, `parser`, `envelope`,
  `instructions`, `schema_fingerprint`, `injector`, `extractor`, and
  `observer`, plus every `Runnable` method.
- `XStructuredMiddleware` exposes `name`, `parser`, `instructions`, and
  `schema_fingerprint`. `repair_prompt` without `repair_config` raises
  `ValueError`; the wrapper raises it when `repair_config` or
  `repair_prompt` is given without `repair`.
- `XStructuredOutputParser` exposes `parser`, `schema_fingerprint`,
  `get_format_instructions()`, and `aparse` / `parse` /
  `aparse_result` / `parse_result`.
- `StructuredParser.parse(text, *, context=...)` parses a whole response;
  `parse_payload(payload, *, context=...)` validates JSON without an
  envelope; `strip_envelopes(text)` returns the prose. Without `envelope=`
  the parser reads bare JSON (recovering it from fences or prose); pass
  `envelope=EnvelopeSpec()` to read `<xstructured>` envelopes.

## Results

`XStructuredResult` (frozen):

| Field | Meaning |
| --- | --- |
| `content` | The prose with every envelope removed. |
| `structured` | The validated value. |
| `raw` | The wrapped Runnable's output, such as the `AIMessage`. |
| `raw_text` | The full response text. |
| `json_text` | The JSON that validated. |
| `recovered` | The JSON came from a fence or surrounding prose. |
| `schema_name` | The matched name, for named schemas. |
| `repaired`, `repair_attempts` | Whether and how often repair ran. |
| `metadata` | `schema_fingerprint`, `envelope_count`, `parse_duration`, and, for messages, `message_id`, `response_metadata`, `usage_metadata`. |

`ParseResult` (from `StructuredParser`): `value`, `raw`, `json_text`,
`recovered`, `envelope_spans`, `schema_name`, `repaired`, `repair_attempts`.

## Stream events

`StreamEvent(kind, sequence, text=None, structured=None, result=None)`, with
`kind` one of `StreamEventKind.TEXT_DELTA`, `STRUCTURED_START`,
`STRUCTURED_DELTA`, `STRUCTURED_END`, `RESULT`. See
[streaming.md](streaming.md).

## Configuration

| Class | Fields (defaults) |
| --- | --- |
| `EnvelopeSpec` | `start="<xstructured>"`, `end="</xstructured>"` |
| `ParserConfig` | `max_input_chars=1_000_000`, `max_envelope_chars=1_000_000`, `max_payload_chars=1_000_000`, `max_nesting_depth=100`, `recovery=RecoveryConfig()`, `require_envelope=False` |
| `RecoveryConfig` | `enabled=True`, `strip_markdown_fences=True`, `strip_surrounding_text=True`, `max_candidates=4` (1 to 4) |
| `RepairConfig` | `enabled=True`, `max_attempts=1` (1 to 5) |
| `SchemaOptions` | `strict`, `extra`, `context`, `by_alias`, `by_name`, `config`, `json_schema_by_alias`, `ref_template`, `union_format`, `schema_generator`, `json_schema_mode` |
| `NamedSchemaSpec` | `schema_key="schema"`, `payload_key="payload"`; pass to `inspect_named_schemas(..., spec=)` |

All are frozen and reject unknown fields.

## Errors

```text
XStructuredError
├── SchemaError          the schema is not a valid target (construction)
├── EnvelopeError        invalid delimiters (construction)
└── ParseError           .text holds the model output
    ├── RecoveryError    .failures: one reason per candidate tried
    ├── LimitExceededError  .limit (field name), .maximum
    └── RepairError      .attempts, .failures; __cause__ is the last error
```

`JsonSafetyError` is a `ValueError` raised by `StrictJsonDecoder` for
documents that are too deep, repeat a key, or use `NaN` or `Infinity`; the
parser reports it inside `RecoveryError.failures`.

## Helpers

- `inspect_schema(schema)`, `inspect_named_schemas(mapping)`: resolve a schema
  once and reuse the `SchemaInfo` / `NamedSchemas`.
- `schema_instructions(schema, ...)`: the instruction text alone.
- `fingerprint_schema(schema)`, `canonical_schema_json(schema)`: a stable
  SHA-256 of the JSON Schema, for cache keys and drift checks.
- `CONTEXT_KEY` (`"xstructured_context"`): run-config key for a per-call
  validation context.
- `INSTRUCTIONS_MESSAGE_ID`: the ID of the system message the default injector
  adds to a `{"messages": [...]}` state.

## Testing

`xstructured.testing.ScriptedChatModel.of(*replies)` replays strings or
`AIMessage` values (tool calls included), streams them word by word, and
accepts `bind_tools`. The `*Contract` classes in the same module test custom
extension points; the `xstructured-extend` skill covers them.
