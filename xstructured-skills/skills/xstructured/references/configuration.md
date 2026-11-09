# Configuration

## Envelopes

The default envelope is `<xstructured>...</xstructured>`. Change it with
`envelope=EnvelopeSpec(start="<result>", end="</result>")`. Delimiters must
differ and must not contain `"` or `\`; named envelopes need tag-style
delimiters. Invalid delimiters raise `EnvelopeError` at construction.

## Limits

`ParserConfig` bounds untrusted output. Exceeding a limit raises
`LimitExceededError` with `.limit` (the field name) and `.maximum`.

```python
from xstructured import ParserConfig, RecoveryConfig

config = ParserConfig(
    max_input_chars=200_000,
    max_payload_chars=20_000,
    max_nesting_depth=20,
    recovery=RecoveryConfig(max_candidates=2),
)
# with_xstructured_output(model, Schema, parser_config=config)
```

The wrapper, middleware, and output parser always require an envelope.
Size limits a little above the largest legitimate response; never raise them
to hide a failure.

## Recovery

When the envelope holds a Markdown fence or prose around the JSON, the default
`ConservativeRecovery` tries, in order: the text as given, the body of a
Markdown fence spanning the whole text, the outermost `{...}`, and the
outermost `[...]`. It never rewrites JSON syntax. The first candidate that
decodes and validates wins.
`RecoveryConfig(enabled=False)` accepts only the exact payload.
`result.recovered` tells you recovery was used.

## Repair

Repair sends an invalid reply back to a model, with the problems found, up to
`max_attempts` (1 to 5) times.

```python
from xstructured import RepairConfig, with_xstructured_output


def make(model, schema):
    return with_xstructured_output(
        model,
        schema,
        repair=model,
        repair_config=RepairConfig(max_attempts=1),
    )
```

- The middleware repairs with the agent's own model: pass `repair_config`
  only.
- Repair calls are traced as child runs tagged `xstructured:repair`.
- `result.repaired` and `result.repair_attempts` report what happened;
  `RepairError` is raised when the budget runs out, with `__cause__` set to
  the last failure.
- Customize the repair input with a `RepairPromptBuilder` subclass
  (`repair_prompt=`).

## Multiple values and named payloads

- `multiple=True`: the envelope holds a JSON array; `structured` is a list.
- A mapping of names to schemas, `{"order": Order, "refund": Refund}`: the
  model answers `{"schema": "<name>", "payload": {...}}` and
  `result.schema_name` says which matched. To rename the keys, pass
  `inspect_named_schemas(mapping, spec=NamedSchemaSpec(schema_key="kind"))`
  as the schema.
- Named schemas with `multiple_envelopes=True`: one
  `<xstructured name="order">...</xstructured>` envelope per applicable
  schema; `structured` is a dict keyed by name. Not streamable.

## Pydantic options

`schema_options=SchemaOptions(...)` forwards options to Pydantic's
`TypeAdapter`, so a schema behaves as it does with Pydantic directly:

| Field | Purpose |
| --- | --- |
| `strict` | Strict validation. |
| `extra` | `"ignore"`, `"allow"`, or `"forbid"` unknown fields. |
| `context` | Default validation context (`info.context`). |
| `by_alias`, `by_name` | Accept aliases and field names. |
| `config` | A `ConfigDict` for annotation targets such as `list[Item]`. |
| `json_schema_by_alias`, `ref_template`, `union_format`, `schema_generator`, `json_schema_mode` | JSON Schema generation. |

A per-call context under `CONTEXT_KEY` in the run config replaces
`context` for that call.

## Instructions

`inject_instructions=False` leaves the input alone; put
`wrapper.instructions` (or `middleware.instructions`) in your own prompt. To
change the wording, pass `renderer=` a `DefaultInstructionRenderer` subclass.
`schema_instructions(schema)` returns the text without building a wrapper.
