"""Envelope delimiter specification."""

from __future__ import annotations

from dataclasses import dataclass

from xstructured.core.errors import EnvelopeError


@dataclass(frozen=True, slots=True)
class EnvelopeSpec:
    """Opening and closing delimiters surrounding a structured payload."""

    start: str = "<xstructured>"
    end: str = "</xstructured>"

    def __post_init__(self) -> None:
        if not self.start or not self.end:
            raise EnvelopeError("Envelope delimiters must be non-empty")
        if self.start == self.end:
            raise EnvelopeError("Envelope delimiters must differ")

    def wrap(self, payload: str) -> str:
        """Wrap *payload* with this specification's delimiters."""
        return f"{self.start}{payload}{self.end}"
