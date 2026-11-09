"""OpenTelemetry tracing (requires the ``otel`` extra).

Install it with ``pip install "xstructured[otel]"`` and pass an
`OpenTelemetryObserver` as the ``observer`` of `with_xstructured_output` or
`XStructuredMiddleware`. Each call becomes one span named
``xstructured <operation>``, a child of the span current when the call starts.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from importlib.metadata import version
from typing import override

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode, Tracer, TracerProvider

from .contracts import AttributeValue, Observation, Observer

__all__ = ["OpenTelemetryObserver"]

_CANCELLATIONS = (asyncio.CancelledError, GeneratorExit, KeyboardInterrupt)


class OpenTelemetryObserver(Observer):
    """Record every call as an OpenTelemetry span.

    Span attributes are sizes, counts, flags, and names, prefixed with
    ``xstructured.``; prompts and responses are never recorded. A failed call
    records the exception and sets the span status to error. A cancelled call
    sets ``xstructured.cancelled`` and leaves the status unset.

    Args:
        tracer_provider: The provider to use. Defaults to the global provider.
    """

    def __init__(
        self, *, tracer_provider: TracerProvider | None = None
    ) -> None:
        self._tracer: Tracer = trace.get_tracer(
            "xstructured",
            version("xstructured"),
            tracer_provider=tracer_provider,
        )

    def __repr__(self) -> str:
        return "OpenTelemetryObserver()"

    @override
    def start(
        self, operation: str, attributes: Mapping[str, AttributeValue]
    ) -> Observation:
        span = self._tracer.start_span(
            f"xstructured {operation}",
            attributes={**attributes, "xstructured.operation": operation},
            record_exception=False,
            set_status_on_exception=False,
        )
        return _SpanObservation(span)


class _SpanObservation(Observation):
    def __init__(self, span: Span) -> None:
        self._span = span

    @override
    def succeed(self, attributes: Mapping[str, AttributeValue]) -> None:
        self._span.set_attributes(dict(attributes))
        self._span.set_status(Status(StatusCode.OK))
        self._span.end()

    @override
    def fail(self, error: BaseException) -> None:
        if isinstance(error, _CANCELLATIONS):
            self._span.set_attribute("xstructured.cancelled", True)  # noqa: FBT003
        else:
            self._span.record_exception(error)
            self._span.set_attribute("error.type", type(error).__qualname__)
            self._span.set_status(Status(StatusCode.ERROR, str(error)))
        self._span.end()
