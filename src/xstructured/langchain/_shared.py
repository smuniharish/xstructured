"""Helpers shared by the Runnable wrapper, the output parser, and the agent middleware."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, override

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig

from xstructured.contracts import AttributeValue, Observation, Observer
from xstructured.core.result import ParseResult, XStructuredResult
from xstructured.schema.introspection import UNSET

__all__ = [
    "CONTEXT_KEY",
    "build_result",
    "observe",
    "remove_spans",
    "result_attributes",
    "validation_context",
]

CONTEXT_KEY = "xstructured_context"
"""``configurable`` key whose value is passed to Pydantic as the validation context."""


class _NullObservation(Observation):
    @override
    def succeed(self, attributes: Mapping[str, AttributeValue]) -> None:
        del attributes

    @override
    def fail(self, error: BaseException) -> None:
        del error


_NULL_OBSERVATION = _NullObservation()


def observe(
    observer: Observer | None,
    operation: str,
    attributes: Mapping[str, AttributeValue],
) -> Observation:
    """Start an observation, or return one that records nothing."""
    if observer is None:
        return _NULL_OBSERVATION
    return observer.start(operation, attributes)


def validation_context(config: RunnableConfig | None) -> Any:
    """Return the validation context set in *config*, or `UNSET`."""
    configurable = (config or {}).get("configurable") or {}
    return configurable.get(CONTEXT_KEY, UNSET)


def remove_spans(text: str, spans: tuple[tuple[int, int], ...]) -> str:
    """Return *text* without the given ``(start, end)`` spans."""
    parts: list[str] = []
    position = 0
    for start, end in spans:
        parts.append(text[position:start])
        position = end
    parts.append(text[position:])
    return "".join(parts)


def build_result[T](
    *,
    fingerprint: str,
    raw: Any,
    raw_text: str,
    content: str,
    parsed: ParseResult[T],
    envelope_count: int,
    parse_duration: float,
) -> XStructuredResult[T]:
    """Return the `XStructuredResult` of one parsed response."""
    metadata: dict[str, Any] = {
        "schema_fingerprint": fingerprint,
        "envelope_count": envelope_count,
        "parse_duration": parse_duration,
    }
    if isinstance(raw, BaseMessage):
        metadata["message_id"] = raw.id
        metadata["response_metadata"] = dict(raw.response_metadata)
        usage = getattr(raw, "usage_metadata", None)
        if usage:
            metadata["usage_metadata"] = dict(usage)
    return XStructuredResult(
        content=content,
        structured=parsed.value,
        raw=raw,
        raw_text=raw_text,
        json_text=parsed.json_text,
        recovered=parsed.recovered,
        schema_name=parsed.schema_name,
        repaired=parsed.repaired,
        repair_attempts=parsed.repair_attempts,
        metadata=MappingProxyType(metadata),
    )


def result_attributes(
    result: XStructuredResult[Any],
) -> dict[str, AttributeValue]:
    """Return telemetry attributes for *result*: sizes, counts, and flags only."""
    attributes: dict[str, AttributeValue] = {
        "xstructured.recovered": result.recovered,
        "xstructured.repaired": result.repaired,
        "xstructured.repair_attempts": result.repair_attempts,
        "xstructured.envelope_count": result.metadata["envelope_count"],
        "xstructured.parse_duration": result.metadata["parse_duration"],
        "xstructured.response_chars": len(result.raw_text),
        "xstructured.content_chars": len(result.content),
    }
    if result.schema_name is not None:
        attributes["xstructured.schema_name"] = result.schema_name
    return attributes
