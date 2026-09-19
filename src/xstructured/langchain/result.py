"""Result type returned by the LangChain integration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class XStructuredResult(Generic[T]):
    """Natural language, validated data, and the unmodified model response."""

    content: str
    structured: T
    raw: Any
    raw_text: str
    json_text: str
    recovered: bool = False
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    schema_name: str | None = None
    """Which named schema matched, when wrapped with multiple named schemas.

    ``None`` when `with_xstructured_output` was called with a single schema
    target.
    """
    repaired: bool = False
    """Whether the optional, bounded LLM repair fallback produced this value.

    Always ``False`` unless a *repair* `Runnable` was supplied to
    `with_xstructured_output` and conservative recovery was exhausted first.
    """
    repair_attempt_count: int = 0

    @property
    def text(self) -> str:
        """Alias for the natural-language content."""
        return self.content
