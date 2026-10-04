from __future__ import annotations

import pytest

from xstructured import EnvelopeError, EnvelopeSpec


@pytest.mark.parametrize(
    ("start", "end", "message"),
    [
        ("", "]]", "non-whitespace"),
        ("[[", "   ", "non-whitespace"),
        ('<a "x">', "</a>", "double quotes or backslashes"),
        ("<a>", "<\\a>", "double quotes or backslashes"),
        ("##", "##", "must differ"),
    ],
)
def test_invalid_delimiters_are_rejected(
    start: str, end: str, message: str
) -> None:
    with pytest.raises(EnvelopeError, match=message):
        EnvelopeSpec(start, end)


def test_wrap_surrounds_a_payload() -> None:
    assert EnvelopeSpec("[[", "]]").wrap("{}") == "[[{}]]"


@pytest.mark.parametrize(
    ("start", "supported"),
    [
        ("<xstructured>", True),
        ("<result>", True),
        ("[[", False),
        ("<a<b>", False),
        ("<>", False),
    ],
)
def test_named_envelopes_need_tag_style_delimiters(
    start: str, supported: bool
) -> None:
    assert EnvelopeSpec(start, "</end>").supports_names is supported


def test_named_delimiters_are_derived_from_the_opening_tag() -> None:
    spec = EnvelopeSpec("<result>", "</result>")

    assert spec.named_prefix == '<result name="'
    assert spec.named_start("finding") == '<result name="finding">'
    assert (
        spec.wrap("{}", name="finding") == '<result name="finding">{}</result>'
    )


def test_names_require_a_tag_style_envelope() -> None:
    with pytest.raises(EnvelopeError, match="tag-style"):
        _ = EnvelopeSpec("[[", "]]").named_prefix


@pytest.mark.parametrize("name", ["", "has space", 'quote"', "x" * 65])
def test_invalid_envelope_names_are_rejected(name: str) -> None:
    with pytest.raises(EnvelopeError, match="Invalid envelope name"):
        EnvelopeSpec().named_start(name)
