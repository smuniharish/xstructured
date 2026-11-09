<!-- docs-test: run -->

# OpenTelemetry

Install the `otel` extra and pass an `OpenTelemetryObserver` as the
`observer` of `with_xstructured_output` or `XStructuredMiddleware`:

```bash
pip install "xstructured[otel]"
```

Each call becomes one span named `xstructured <operation>` (`invoke`,
`stream`, `transform`, or `agent`), a child of the span current when the call
starts. Without a `tracer_provider`, the observer uses the global provider, so
it follows whatever OpenTelemetry setup your application already has.

```python
import asyncio

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from pydantic import BaseModel

from xstructured import ParseError, with_xstructured_output
from xstructured.otel import OpenTelemetryObserver
from xstructured.testing import ScriptedChatModel


class Routing(BaseModel):
    queue: str
    urgent: bool


exporter = InMemorySpanExporter()
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(exporter))
observer = OpenTelemetryObserver(tracer_provider=provider)

model = ScriptedChatModel.of(
    'Billing. <xstructured>{"queue": "billing", "urgent": false}</xstructured>'
)
router = with_xstructured_output(
    model, Routing, observer=observer, name="ticket-router"
)
asyncio.run(router.ainvoke("I was charged twice."))

(span,) = exporter.get_finished_spans()
assert span.name == "xstructured invoke"
assert span.status.is_ok
attributes = dict(span.attributes or {})
assert attributes["xstructured.name"] == "ticket-router"
assert attributes["xstructured.envelope_count"] == 1
assert attributes["xstructured.schema_fingerprint"] == router.schema_fingerprint
```

## Attributes

Span attributes are the observation attributes listed in
[Observability](../guide/observability.md#observers), plus
`xstructured.operation`. They hold sizes, counts, flags, durations, and names;
prompts, responses, and parsed values are never recorded.

## Failures

A failed call records the exception, sets `error.type` to the exception class,
and sets the span status to error. A cancelled call, or a stream the caller
stops early, sets `xstructured.cancelled` and leaves the status unset.

```python
exporter.clear()
failing = with_xstructured_output(
    ScriptedChatModel.of("No idea."), Routing, observer=observer
)
try:
    asyncio.run(failing.ainvoke("Where does this go?"))
except ParseError:
    pass

(span,) = exporter.get_finished_spans()
assert not span.status.is_ok
assert dict(span.attributes or {})["error.type"] == "ParseError"
```

## Exporting

Add an OTLP exporter to send spans to a collector, Jaeger, or any OTLP backend.
The [OpenTelemetry tracing example](../examples/opentelemetry-tracing.md)
exports to the endpoint in `OTEL_EXPORTER_OTLP_ENDPOINT` and shows how to run
Jaeger locally.
