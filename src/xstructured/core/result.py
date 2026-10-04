"""Result types."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

__all__ = ["ParseResult", "XStructuredResult"]


def _empty_metadata() -> Mapping[str, Any]:
    return MappingProxyType({})


@dataclass(frozen=True, slots=True)
class ParseResult[T]:
    """A validated value and how it was extracted from the response.

    Attributes:
        value: The schema-validated value.
        raw: The text that was parsed.
        json_text: The exact JSON text that validated. For named envelopes this is a JSON
            object keyed by envelope name whose values are the validated payload texts.
        recovered: Whether a recovery candidate other than the text as given produced
            the value.
        envelope_spans: ``(start, end)`` offsets of each envelope in `raw`, delimiters
            included.
        schema_name: The matched name when parsing against named schemas, otherwise
            ``None``.
        repaired: Whether the opt-in LLM-assisted repair produced the value.
        repair_attempts: Number of repair calls used to produce the value.
    """

    value: T
    raw: str
    json_text: str
    recovered: bool = False
    envelope_spans: tuple[tuple[int, int], ...] = ()
    schema_name: str | None = None
    repaired: bool = False
    repair_attempts: int = 0

    @property
    def envelope_found(self) -> bool:
        """Whether the value was read from at least one envelope."""
        return bool(self.envelope_spans)


@dataclass(frozen=True, slots=True)
class XStructuredResult[T]:
    """The outcome of a wrapped Runnable: prose, validated data, and provenance.

    Attributes:
        content: Natural-language text of the response with every envelope removed.
        structured: The schema-validated value.
        raw: The wrapped Runnable's original output. For a stream of message chunks this
            is the merged message.
        raw_text: The text extracted from `raw`.
        json_text: The JSON text that validated (see `ParseResult.json_text`).
        recovered: Whether conservative recovery was needed.
        schema_name: The matched name when using named schemas, otherwise ``None``.
        repaired: Whether the opt-in LLM-assisted repair produced the value.
        repair_attempts: Number of repair calls used to produce the value.
        metadata: Read-only operational metadata: ``schema_fingerprint``,
            ``envelope_count``, ``parse_duration`` (seconds), and, for message outputs,
            ``message_id``, ``response_metadata`` and ``usage_metadata``.
    """

    content: str
    structured: T
    raw: Any
    raw_text: str
    json_text: str
    recovered: bool = False
    schema_name: str | None = None
    repaired: bool = False
    repair_attempts: int = 0
    metadata: Mapping[str, Any] = field(default_factory=_empty_metadata)
