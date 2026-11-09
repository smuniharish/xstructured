"""Conservative recovery candidates for model-produced JSON."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import override

from xstructured.contracts import RecoveryStrategy

__all__ = ["ConservativeRecovery"]

_FENCE = re.compile(
    r"\A\s*```(?:json)?[ \t]*\n(?P<body>.*?)\n?```\s*\Z",
    re.DOTALL | re.IGNORECASE,
)


class ConservativeRecovery(RecoveryStrategy):
    """Yield distinct, non-empty substrings of the text in a fixed order.

    The order is: the text as given, the body of a Markdown code fence that spans
    the whole text, the outermost ``{...}`` substring, and the outermost
    ``[...]`` substring. Candidates are always substrings of the text (stripped
    of surrounding whitespace); JSON syntax is never rewritten.

    Args:
        strip_markdown_fences: Try the body of a whole-text Markdown code fence.
        strip_surrounding_text: Try the outermost object and array substrings.
    """

    def __init__(
        self,
        *,
        strip_markdown_fences: bool = True,
        strip_surrounding_text: bool = True,
    ) -> None:
        self.strip_markdown_fences = strip_markdown_fences
        self.strip_surrounding_text = strip_surrounding_text

    def __repr__(self) -> str:
        return (
            "ConservativeRecovery("
            f"strip_markdown_fences={self.strip_markdown_fences}, "
            f"strip_surrounding_text={self.strip_surrounding_text})"
        )

    @override
    def candidates(self, text: str) -> Iterator[str]:
        seen: set[str] = set()

        def emit(candidate: str) -> Iterator[str]:
            candidate = candidate.strip()
            if candidate and candidate not in seen:
                seen.add(candidate)
                yield candidate

        yield from emit(text)
        if (
            self.strip_markdown_fences
            and (match := _FENCE.match(text)) is not None
        ):
            yield from emit(match.group("body"))
        if self.strip_surrounding_text:
            for opening, closing in (("{", "}"), ("[", "]")):
                start = text.find(opening)
                end = text.rfind(closing)
                if 0 <= start < end:
                    yield from emit(text[start : end + 1])
