"""Result values returned by structured parsing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ParseResult(Generic[T]):
    """A validated value and the exact parsing path used to produce it."""

    value: T
    raw: str
    json_text: str
    recovered: bool = False
    envelope_found: bool = False
    schema_name: str | None = None
    """The matched schema name, when parsing against named multiple schemas.

    ``None`` when the parser was constructed with a single schema target.
    """
    repaired: bool = False
    """Whether this value came from the optional, bounded LLM repair fallback.

    Always ``False`` for a plain `StructuredParser.parse` call; only ever
    ``True`` when `xstructured.langchain.repair.Repairer` produced the value
    after conservative recovery was exhausted.
    """
    repair_attempt_count: int = 0
