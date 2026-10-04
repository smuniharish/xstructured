"""Envelope delimiter specification."""

from __future__ import annotations

import re
from dataclasses import dataclass

from xstructured.core.errors import EnvelopeError

__all__ = ["NAME_PATTERN", "EnvelopeSpec"]

NAME_PATTERN = re.compile(r"[A-Za-z0-9_.-]{1,64}")
"""Allowed characters and length for schema and envelope names."""

_FORBIDDEN = ('"', "\\")
_TAG = re.compile(r"<[^<>]+>")


@dataclass(frozen=True, slots=True)
class EnvelopeSpec:
    """Opening and closing delimiters around a structured payload.

    Delimiters must be distinct, contain a non-whitespace character, and must not
    contain double quotes or backslashes, so they can never be confused with JSON
    string content. Tag-style delimiters such as ``<result>`` / ``</result>`` also
    support named envelopes (``<result name="finding">``).

    Attributes:
        start: The opening delimiter.
        end: The closing delimiter.

    Raises:
        EnvelopeError: If the delimiters are invalid.
    """

    start: str = "<xstructured>"
    end: str = "</xstructured>"

    def __post_init__(self) -> None:
        for delimiter in (self.start, self.end):
            if not delimiter.strip():
                raise EnvelopeError(
                    "Envelope delimiters must contain non-whitespace characters"
                )
            if any(character in delimiter for character in _FORBIDDEN):
                raise EnvelopeError(
                    "Envelope delimiters must not contain double quotes or backslashes"
                )
        if self.start == self.end:
            raise EnvelopeError("Envelope delimiters must differ")

    @property
    def supports_names(self) -> bool:
        """Whether the opening delimiter is tag-style and can carry a ``name``."""
        return _TAG.fullmatch(self.start) is not None

    @property
    def named_prefix(self) -> str:
        """The text that starts every named opening delimiter, up to the name.

        Raises:
            EnvelopeError: If the delimiters are not tag-style.
        """
        if not self.supports_names:
            raise EnvelopeError(
                f"Named envelopes need tag-style delimiters such as '<result>', not {self.start!r}"
            )
        return f'{self.start[:-1]} name="'

    def named_start(self, name: str) -> str:
        """Return the opening delimiter of the envelope named *name*.

        Raises:
            EnvelopeError: If the delimiters are not tag-style or *name* is invalid.
        """
        if NAME_PATTERN.fullmatch(name) is None:
            raise EnvelopeError(f"Invalid envelope name {name!r}")
        return f'{self.named_prefix}{name}">'

    def wrap(self, payload: str, *, name: str | None = None) -> str:
        """Wrap *payload* in this envelope, optionally as the envelope named *name*."""
        start = self.start if name is None else self.named_start(name)
        return f"{start}{payload}{self.end}"
