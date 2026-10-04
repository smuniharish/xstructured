"""Differential tests: the optimized scanners must agree with a per-character oracle."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from xstructured._scan import StringState, nesting_exceeds, scan_for_delimiter

JSONISH = st.text(alphabet='"\\<>/x[]{}: a', max_size=60)
DELIMITERS = st.sampled_from(["</x>", "]]", "<x>", "x", "<<END>>"])
STATES = st.builds(StringState, st.booleans(), st.booleans()).filter(
    lambda state: state.in_string or not state.escaped
)


def reference_scan(
    text: str, delimiter: str, start: int, state: StringState
) -> tuple[int, int, StringState]:
    limit = len(text) - len(delimiter) + 1
    in_string, escaped = state
    position = start
    while position < limit:
        character = text[position]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif text.startswith(delimiter, position):
            return position, position, StringState()
        position += 1
    return -1, position, StringState(in_string, escaped)


def reference_nesting_exceeds(text: str, maximum: int) -> bool:
    depth = 0
    in_string = escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > maximum:
                return True
        elif character in "]}":
            depth -= 1
    return False


@given(text=JSONISH, delimiter=DELIMITERS, state=STATES, data=st.data())
def test_delimiter_scan_matches_the_oracle(
    text: str, delimiter: str, state: StringState, data: st.DataObject
) -> None:
    start = data.draw(st.integers(min_value=0, max_value=len(text)))

    assert tuple(
        scan_for_delimiter(text, delimiter, start=start, state=state)
    ) == (reference_scan(text, delimiter, start, state))


@given(
    text=JSONISH,
    delimiter=DELIMITERS,
    cut=st.integers(min_value=0, max_value=60),
)
def test_resumed_scans_find_the_same_delimiter(
    text: str, delimiter: str, cut: int
) -> None:
    whole = scan_for_delimiter(text, delimiter).index
    first = scan_for_delimiter(text[:cut], delimiter)
    if first.index >= 0:
        assert first.index == whole
        return
    rest = text[first.position :]
    second = scan_for_delimiter(rest, delimiter, state=first.state)

    assert (second.index + first.position if second.index >= 0 else -1) == whole


@given(text=JSONISH, maximum=st.integers(min_value=0, max_value=6))
def test_nesting_check_matches_the_oracle(text: str, maximum: int) -> None:
    assert nesting_exceeds(text, maximum) is reference_nesting_exceeds(
        text, maximum
    )
