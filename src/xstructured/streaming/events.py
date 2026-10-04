"""Typed events of the streaming protocol."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xstructured.core.result import XStructuredResult

__all__ = ["StreamEvent", "StreamEventKind"]


class StreamEventKind(StrEnum):
    """Stable names of the streaming protocol events, in lifecycle order."""

    TEXT_DELTA = "text_delta"
    """Natural-language text outside the envelope."""
    STRUCTURED_START = "structured_start"
    """The opening delimiter was found."""
    STRUCTURED_DELTA = "structured_delta"
    """Raw payload text inside the envelope."""
    STRUCTURED_END = "structured_end"
    """The closing delimiter was found and the payload validated."""
    RESULT = "result"
    """The complete result, emitted once after the stream ends."""


@dataclass(frozen=True, slots=True)
class StreamEvent[T]:
    """One ordered event of an xstructured response stream.

    Attributes:
        kind: The event kind.
        sequence: Zero-based position of the event in the stream.
        text: The text of `TEXT_DELTA` and `STRUCTURED_DELTA` events.
        structured: The validated value of the `STRUCTURED_END` event.
        result: The complete `XStructuredResult` of the `RESULT` event.
    """

    kind: StreamEventKind
    sequence: int
    text: str | None = None
    structured: T | None = None
    result: XStructuredResult[T] | None = None
