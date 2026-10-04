"""Envelope delimiters and incremental envelope scanning."""

from .scanner import EnvelopeScanner, EnvelopeState, ScanEvent
from .spec import NAME_PATTERN, EnvelopeSpec

__all__ = [
    "NAME_PATTERN",
    "EnvelopeScanner",
    "EnvelopeSpec",
    "EnvelopeState",
    "ScanEvent",
]
