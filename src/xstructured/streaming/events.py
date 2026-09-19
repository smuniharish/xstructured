"""Typed events emitted while decoding an xstructured response."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class StreamEventKind(StrEnum):
    """Stable event names for the streaming protocol lifecycle."""

    TEXT_DELTA = "text_delta"
    STRUCTURED_START = "structured_start"
    STRUCTURED_DELTA = "structured_delta"
    STRUCTURED_END = "structured_end"
    RESULT = "result"


@dataclass(frozen=True, slots=True)
class StreamEvent(Generic[T]):
    """One ordered event from an xstructured response stream."""

    kind: StreamEventKind
    sequence: int
    text: str | None = None
    structured: T | None = None
    result: Any | None = None
