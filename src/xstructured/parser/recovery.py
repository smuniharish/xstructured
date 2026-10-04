"""Conservative recovery candidates for model-produced JSON."""

from __future__ import annotations

import re
from collections.abc import Iterator

__all__ = ["recovery_candidates"]

_FENCE = re.compile(
    r"\A\s*```(?:json)?[ \t]*\n(?P<body>.*?)\n?```\s*\Z",
    re.DOTALL | re.IGNORECASE,
)


def recovery_candidates(
    text: str,
    *,
    strip_markdown_fences: bool = True,
    strip_surrounding_text: bool = True,
) -> Iterator[str]:
    """Yield distinct, non-empty candidate substrings of *text* in a fixed order.

    The order is: the text as given, the body of a Markdown code fence that spans the
    whole text, the outermost ``{...}`` substring, and the outermost ``[...]``
    substring. Candidates are always substrings of *text* (stripped of surrounding
    whitespace); JSON syntax is never rewritten.
    """
    seen: set[str] = set()

    def emit(candidate: str) -> Iterator[str]:
        candidate = candidate.strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            yield candidate

    yield from emit(text)
    if strip_markdown_fences and (match := _FENCE.match(text)) is not None:
        yield from emit(match.group("body"))
    if strip_surrounding_text:
        for opening, closing in (("{", "}"), ("[", "]")):
            start = text.find(opening)
            end = text.rfind(closing)
            if 0 <= start < end:
                yield from emit(text[start : end + 1])
