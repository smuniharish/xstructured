"""Domain-specific exceptions with parse context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class XStructuredError(Exception):
    """Base exception for xstructured failures."""


class SchemaError(XStructuredError):
    """Raised when a schema target cannot be introspected or validated."""


class EnvelopeError(XStructuredError):
    """Raised for invalid envelope specifications or envelope extraction."""


@dataclass(eq=False)
class ParseError(XStructuredError):
    """Raised when content cannot be parsed as JSON."""

    message: str
    text: str
    cause: Exception | None = None

    def __str__(self) -> str:
        return self.message


@dataclass(eq=False)
class RecoveryError(ParseError):
    """Raised after every configured recovery candidate has failed."""

    attempts: tuple[str, ...] = ()
    validation_errors: Any | None = None


@dataclass(eq=False)
class RepairError(ParseError):
    """Raised when bounded, opt-in LLM-assisted repair exhausts its attempts.

    Only raised when a repair ``Runnable`` was explicitly configured (see
    ``RepairConfig``); repair is never attempted, and this error is never
    raised, by default.
    """

    attempt_count: int = 0
    repair_errors: tuple[str, ...] = ()
