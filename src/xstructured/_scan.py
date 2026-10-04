"""JSON-aware text scanning shared by envelopes, streaming, and JSON safety checks.

Text is treated as JSON-like: double-quoted strings may contain backslash escapes, and
delimiters or brackets inside strings are ignored. Every scan runs as a few
compiled-regex matches, so its cost is linear in the text length and does not grow with
the number of strings. Possessive quantifiers keep the patterns free of backtracking,
even for unterminated strings.
"""

from __future__ import annotations

import re
import sys
from functools import lru_cache
from itertools import accumulate
from typing import NamedTuple, cast

_STRING = r'"(?:[^"\\]++|\\.)*+"'
# A string body: stops at a quote, at a backslash with nothing after it, or at the end.
_BODY = re.compile(r'(?:[^"\\]++|\\.)*+', re.DOTALL)
# Text outside strings: stops at the opening quote of a string that does not close.
_OUTSIDE = re.compile(rf'(?:[^"]++|{_STRING})*+', re.DOTALL)
# Everything except brackets outside strings (unterminated strings included).
_NOT_BRACKETS = re.compile(
    r'"(?:[^"\\]++|\\.)*+(?:"|\\?\Z)|[^\[\]{}"]++', re.DOTALL
)
_DEPTH = {"[": 1, "{": 1, "]": -1, "}": -1}


class StringState(NamedTuple):
    """Whether a scan position is inside a JSON string, and just after a backslash."""

    in_string: bool = False
    escaped: bool = False


OUTSIDE = StringState()


class DelimiterScan(NamedTuple):
    """Result of `scan_for_delimiter`.

    Attributes:
        index: Index of the delimiter, or ``-1`` when it was not found.
        position: Where the scan stopped: `index` when found, otherwise the first index
            at which the delimiter could still begin once more text arrives. Text before
            `position` has been fully inspected.
        state: The string state at `position`.
    """

    index: int
    position: int
    state: StringState


@lru_cache(maxsize=64)
def _outside_until(delimiter: str) -> re.Pattern[str]:
    """Match text outside strings up to *delimiter* or an unterminated string."""
    first, rest = re.escape(delimiter[0]), re.escape(delimiter[1:])
    stop = f"(?!{rest})" if rest else "(?!)"
    return re.compile(
        rf'(?:[^"{first}]++|{_STRING}|{first}{stop})*+', re.DOTALL
    )


def _match_end(
    pattern: re.Pattern[str], text: str, start: int, end: int = sys.maxsize
) -> int:
    # Every scanning pattern is a single `(...)*+` repetition, so it always matches.
    return cast("re.Match[str]", pattern.match(text, start, end)).end()


def scan_for_delimiter(
    text: str,
    delimiter: str,
    *,
    start: int = 0,
    state: StringState = OUTSIDE,
) -> DelimiterScan:
    """Find *delimiter* outside JSON strings in ``text[start:]``.

    The delimiter must not contain double quotes or backslashes. *state* is the string
    state at *start*, which lets a caller resume a scan across chunk boundaries.
    """
    limit = max(len(text) - len(delimiter) + 1, start)
    position = start
    if state.in_string and position < limit:
        body = _match_end(_BODY, text, position + state.escaped)
        position = body + 1 if body < limit and text[body] == '"' else limit
    if position < limit:
        end = _match_end(_outside_until(delimiter), text, position)
        if text.startswith(delimiter, end):
            return DelimiterScan(end, end, OUTSIDE)
    return DelimiterScan(-1, limit, string_state(text, start, limit, state))


def string_state(
    text: str, start: int, end: int, state: StringState = OUTSIDE
) -> StringState:
    """Return the string state at *end* after scanning ``text[start:end]`` from *state*."""
    position = start
    if position >= end:
        return state
    if state.in_string:
        body = _match_end(_BODY, text, position + state.escaped, end)
        if body >= end:
            return StringState(in_string=True)
        if text[body] == "\\":
            return StringState(in_string=True, escaped=True)
        position = body + 1
    stop = _match_end(_OUTSIDE, text, position, end)
    if stop >= end:
        return OUTSIDE
    body = _match_end(_BODY, text, stop + 1, end)
    return StringState(in_string=True, escaped=body < end)


def nesting_exceeds(text: str, maximum: int) -> bool:
    """Return whether JSON array/object nesting in *text* goes deeper than *maximum*."""
    brackets = _NOT_BRACKETS.sub("", text)
    return (
        bool(brackets)
        and max(accumulate(map(_DEPTH.__getitem__, brackets))) > maximum
    )
