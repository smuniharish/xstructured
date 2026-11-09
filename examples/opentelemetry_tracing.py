"""Trace structured-output calls with OpenTelemetry.

``OpenTelemetryObserver`` records each call as a span named
``xstructured <operation>``, a child of the span current when the call
starts. Span attributes are sizes, counts, flags, and names; prompts and
responses are never recorded.

The spans are printed here. Set ``OTEL_EXPORTER_OTLP_ENDPOINT`` (for example
``http://localhost:4318``) to also export them to a collector, Jaeger, or any
OTLP backend.

Run it with ``uv run python examples/opentelemetry_tracing.py``.
"""

from __future__ import annotations

import asyncio
import os

from langchain_core.messages import HumanMessage
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from pydantic import BaseModel

from _shared import banner, chat_model
from xstructured import with_xstructured_output
from xstructured.otel import OpenTelemetryObserver

SCRIPTED_REPLY = (
    "This is a billing question about a duplicate charge.\n"
    "<xstructured>"
    '{"queue": "billing", "urgent": false}'
    "</xstructured>"
)


class Routing(BaseModel):
    """Where a support ticket goes."""

    queue: str
    urgent: bool


async def main() -> None:
    provider = TracerProvider(
        resource=Resource.create({"service.name": "xstructured-example"})
    )
    spans = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(spans))
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    tracer = provider.get_tracer("support-desk")

    async with chat_model(SCRIPTED_REPLY) as model:
        router = with_xstructured_output(
            model,
            Routing,
            observer=OpenTelemetryObserver(tracer_provider=provider),
            name="ticket-router",
        )
        with tracer.start_as_current_span("route ticket"):
            result = await router.ainvoke(
                [
                    HumanMessage(
                        "I was charged twice for my May subscription. Say "
                        "which team handles it in one sentence."
                    )
                ]
            )
    provider.shutdown()

    banner("OpenTelemetry tracing")
    print(f"Routing: {result.structured!r}")
    for span in spans.get_finished_spans():
        attributes = dict(span.attributes or {})
        print(
            f"span {span.name!r}: status={span.status.status_code.name} "
            f"envelopes={attributes.get('xstructured.envelope_count', '-')} "
            f"name={attributes.get('xstructured.name', '-')}"
        )


if __name__ == "__main__":
    asyncio.run(main())
