# Observers

An observer turns every wrapper call and every final agent answer into one
`Observation`. Use it for metrics, logs, or any tracing backend other than
OpenTelemetry (which ships as `xstructured.otel.OpenTelemetryObserver`).

## Lifecycle

1. The call starts: `observer.start(operation, attributes)`. Attributes at
   start: `xstructured.name`, `xstructured.schema_fingerprint`,
   `xstructured.multiple`, `xstructured.multiple_envelopes`.
2. The call ends, exactly once:
   - `observation.succeed(attributes)` with `xstructured.recovered`,
     `xstructured.repaired`, `xstructured.repair_attempts`,
     `xstructured.envelope_count`, `xstructured.parse_duration` (seconds),
     `xstructured.response_chars`, `xstructured.content_chars`, and
     `xstructured.schema_name` for named schemas;
   - or `observation.fail(error)` with the exception. A consumer that stops a
     stream early, or a cancelled task, gives `GeneratorExit` or
     `asyncio.CancelledError`.

Attribute values are `str`, `bool`, `int`, or `float` (`AttributeValue`), and
never contain prompt or response text. Keep it that way in your own
attributes.

## Writing one

Start from `assets/observer_template.py`:

- Keep `start` cheap and non-blocking; it runs on the event loop.
- Return a new observation per call; concurrent calls overlap.
- Guard against double finishing, and never raise from `succeed` or `fail`.
  Log backend errors instead.
- Count cancellations apart from errors; they are not failures of the model.
- Use the schema fingerprint, not the schema name, as a stable label: named
  schemas set `xstructured.schema_name` only on success.
- Bound label cardinality: never use free text as a metric label.

## Wiring

```python
from xstructured import with_xstructured_output
from xstructured.agents import XStructuredMiddleware

observer = MetricsObserver()
# with_xstructured_output(model, Schema, observer=observer)
# XStructuredMiddleware(Schema, observer=observer)
```

One observer instance can serve every wrapper and middleware in the process.
To combine OpenTelemetry with your own metrics, write an observer that starts
both and finishes both.

## Testing

`ObserverContract` checks the type, a success, a failure, and a
cancellation. Add an end-to-end test that runs a wrapper with
`ScriptedChatModel` and asserts what your backend received, as
`assets/test_extensions.py` does.
