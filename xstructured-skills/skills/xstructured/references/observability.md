# Observability

## Result metadata

Every `XStructuredResult` has `metadata` with `schema_fingerprint`,
`envelope_count`, and `parse_duration`; for message outputs also
`message_id`, `response_metadata`, and `usage_metadata` (token usage, merged
across streamed chunks).

## LangChain tracing

The wrapper is a traced Runnable: with LangSmith or any callback handler,
each call is one run (name it with `.with_config(run_name=...)`), the wrapped
Runnable is a child run, and repair calls are child runs tagged
`xstructured:repair`. Nothing extra is needed.

## Observers

Pass `observer=` to the wrapper or the middleware. The observer's
`start(operation, attributes)` returns an `Observation`, which is finished
exactly once with `succeed(attributes)` or `fail(error)`.

- `operation` is `"invoke"` (invoke, ainvoke, and batches), `"stream"`,
  `"transform"`, or `"agent"` (the middleware, once per final answer).
- Attributes are sizes, counts, flags, and names, never prompt or response
  text:

| Attribute | Set at |
| --- | --- |
| `xstructured.name`, `xstructured.schema_fingerprint`, `xstructured.multiple`, `xstructured.multiple_envelopes` | start |
| `xstructured.recovered`, `xstructured.repaired`, `xstructured.repair_attempts`, `xstructured.envelope_count`, `xstructured.parse_duration`, `xstructured.response_chars`, `xstructured.content_chars` | success |
| `xstructured.schema_name` | success, named schemas only |

- A stream stopped early, or a cancelled task, finishes with `fail`.
- To send metrics to another backend, subclass `Observer`; the
  `xstructured-extend` skill has a template and its contract tests.

## OpenTelemetry

Install `xstructured[otel]` and pass `OpenTelemetryObserver()`. It uses the
global tracer provider unless you pass `tracer_provider=`.

```python
from xstructured import with_xstructured_output
from xstructured.otel import OpenTelemetryObserver


def traced(model, schema):
    return with_xstructured_output(
        model, schema, observer=OpenTelemetryObserver()
    )
```

- One span per call, named `xstructured <operation>`, carrying the
  attributes above plus `xstructured.operation`. Success sets status `OK`.
- A failure sets status `ERROR`, records the exception, and sets
  `error.type` to its class name (for example `ParseError`). A cancellation
  sets `xstructured.cancelled` and leaves the status unset.
- Configure the SDK and exporter (for example
  `opentelemetry-exporter-otlp` with `OTEL_EXPORTER_OTLP_ENDPOINT`) in the
  application; xstructured depends only on `opentelemetry-api`.
