from __future__ import annotations

import pytest

from xstructured._scan import (
    OUTSIDE,
    StringState,
    nesting_exceeds,
    scan_for_delimiter,
)


def test_finds_a_delimiter_outside_strings() -> None:
    scan = scan_for_delimiter('{"a": 1}</x> tail', "</x>")

    assert scan == (8, 8, OUTSIDE)


def test_ignores_delimiters_inside_strings_and_escaped_quotes() -> None:
    text = r'{"a": "</x> and \" </x>"}</x>'

    assert scan_for_delimiter(text, "</x>").index == len(text) - 4


def test_reports_the_safe_boundary_when_the_delimiter_is_missing() -> None:
    scan = scan_for_delimiter('{"a": 1} </', "</x>")

    assert scan.index == -1
    assert scan.position == len('{"a": 1} </') - 3
    assert scan.state == OUTSIDE


def test_reports_string_state_at_the_boundary() -> None:
    scan = scan_for_delimiter('{"a": "unterminated text', "</x>")

    assert scan.index == -1
    assert scan.state == StringState(in_string=True, escaped=False)


def test_reports_an_escape_that_ends_at_the_boundary() -> None:
    text = '{"a": "x\\' + "123"
    scan = scan_for_delimiter(text, "</x>")

    assert scan.position == len(text) - 3
    assert scan.state == StringState(in_string=True, escaped=True)


def test_resumes_inside_a_string_across_chunks() -> None:
    first = scan_for_delimiter('{"a": "</x', "</x>")
    rest = '{"a": "</x'[first.position :] + '>"}</x>'
    second = scan_for_delimiter(rest, "</x>", state=first.state)

    assert second.index == len(rest) - 4


def test_resumes_after_an_escape_split_across_chunks() -> None:
    second = scan_for_delimiter(
        '"</x>"}</x>', "</x>", state=StringState(True, True)
    )

    assert second.index == 7


def test_text_shorter_than_the_delimiter_is_not_consumed() -> None:
    assert scan_for_delimiter("</", "</x>") == (-1, 0, OUTSIDE)


def test_scan_can_start_at_an_offset() -> None:
    assert scan_for_delimiter("</x>abc</x>", "</x>", start=1).index == 7


def test_string_scan_stops_at_the_limit_without_a_closing_quote() -> None:
    scan = scan_for_delimiter('"abcdefgh', "</x>")

    assert scan == (-1, len('"abcdefgh') - 3, StringState(True, False))


@pytest.mark.parametrize(
    ("text", "maximum", "expected"),
    [
        ("[[1]]", 2, False),
        ("[[[1]]]", 2, True),
        ('{"a": "[[[[[[" }', 1, False),
        ('{"a": "\\"[[[[" }', 1, False),
        ('["unterminated [[[[', 1, False),
        ('"\\', 1, False),
        ("]]][[", 2, False),
        ("", 1, False),
    ],
)
def test_nesting_depth_ignores_string_content(
    text: str, maximum: int, expected: bool
) -> None:
    assert nesting_exceeds(text, maximum) is expected
