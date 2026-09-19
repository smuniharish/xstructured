"""Conservative candidate extraction for model-produced JSON."""

from __future__ import annotations

import re
from collections.abc import Iterator

_FENCE = re.compile(r"^\s*```(?:json)?\s*\n(?P<body>.*?)\n?```\s*$", re.DOTALL | re.IGNORECASE)


def recovery_candidates(
    text: str, *, strip_markdown_fences: bool = True, strip_surrounding_text: bool = True
) -> Iterator[str]:
    """Yield distinct plausible JSON documents without altering JSON syntax."""
    seen: set[str] = set()

    def emit(candidate: str) -> Iterator[str]:
        candidate = candidate.strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            yield candidate

    yield from emit(text)
    stripped = text.strip()
    if strip_markdown_fences:
        match = _FENCE.match(stripped)
        if match:
            yield from emit(match.group("body"))
    if strip_surrounding_text:
        for opening, closing in (("{", "}"), ("[", "]")):
            start = stripped.find(opening)
            end = stripped.rfind(closing)
            if start >= 0 and end > start:
                yield from emit(stripped[start : end + 1])
