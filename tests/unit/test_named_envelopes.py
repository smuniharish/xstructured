from __future__ import annotations

import json
from typing import Any

import pytest

from tests.support import Answer, Label
from xstructured import (
    EnvelopeSpec,
    LimitExceededError,
    ParseError,
    ParserConfig,
    ParseResult,
    RecoveryError,
    StructuredParser,
)

SCHEMAS = {"answer": Answer, "label": Label}


def named(
    text: str, config: ParserConfig | None = None
) -> ParseResult[dict[str, Any]]:
    return StructuredParser(
        SCHEMAS, multiple_envelopes=True, config=config
    ).parse(text)


def test_named_envelopes_map_to_their_schemas() -> None:
    text = (
        "Analysis:\n"
        '<xstructured name="answer">{"value": 1}</xstructured>\n'
        "Action:\n"
        '<xstructured name="label">{"name": "ship"}</xstructured>'
    )
    result = StructuredParser(SCHEMAS, multiple_envelopes=True).parse(text)

    assert result.value == {
        "answer": Answer(value=1),
        "label": Label(name="ship"),
    }
    assert json.loads(result.json_text) == {
        "answer": {"value": 1},
        "label": {"name": "ship"},
    }
    assert [text[start:end] for start, end in result.envelope_spans] == [
        '<xstructured name="answer">{"value": 1}</xstructured>',
        '<xstructured name="label">{"name": "ship"}</xstructured>',
    ]
    assert not result.recovered


def test_custom_tag_style_envelopes_are_honored() -> None:
    parser = StructuredParser(
        SCHEMAS, multiple_envelopes=True, envelope=EnvelopeSpec("<r>", "</r>")
    )

    assert parser.parse('<r name="answer">{"value": 2}</r>').value == {
        "answer": Answer(value=2)
    }


def test_closing_tag_inside_a_json_string_does_not_truncate() -> None:
    result = named(
        '<xstructured name="label">{"name": "a </xstructured> b"}</xstructured>'
    )

    assert result.value == {"label": Label(name="a </xstructured> b")}


def test_recovery_applies_inside_named_envelopes() -> None:
    result = named(
        '<xstructured name="answer">\n```json\n{"value": 3}\n```\n</xstructured>'
    )

    assert result.value == {"answer": Answer(value=3)}
    assert result.recovered


@pytest.mark.parametrize(
    ("text", "error", "message"),
    [
        ("no envelopes", ParseError, "No named"),
        (
            '<xstructured name="answer">{"value": 1}',
            ParseError,
            "'answer' is not closed",
        ),
        (
            '<xstructured name="answer',
            ParseError,
            "opening delimiter is not closed",
        ),
        (
            '<xstructured name="other">{}</xstructured>',
            ParseError,
            "Unknown named envelope",
        ),
        (
            (
                '<xstructured name="answer">{"value": 1}</xstructured>'
                '<xstructured name="answer">{"value": 2}</xstructured>'
            ),
            ParseError,
            "Duplicate named envelope",
        ),
        (
            '<xstructured name="answer">{"value": "x"}</xstructured>',
            RecoveryError,
            "in named envelope 'answer'",
        ),
    ],
)
def test_named_envelope_errors(
    text: str, error: type[Exception], message: str
) -> None:
    with pytest.raises(error, match=message):
        named(text)


def test_named_envelope_limits_are_enforced() -> None:
    text = '<xstructured name="answer">{"value": 1}</xstructured>'

    with pytest.raises(LimitExceededError, match="payload exceeds"):
        named(text, config=ParserConfig(max_payload_chars=5))
    with pytest.raises(LimitExceededError, match="'answer' exceeds"):
        named(text, config=ParserConfig(max_envelope_chars=20))


def test_named_envelopes_cannot_use_parse_payload() -> None:
    with pytest.raises(ValueError, match="named envelopes"):
        StructuredParser(SCHEMAS, multiple_envelopes=True).parse_payload("{}")


def test_strip_envelopes_removes_named_envelopes() -> None:
    parser = StructuredParser(SCHEMAS, multiple_envelopes=True)

    assert (
        parser.strip_envelopes(
            'A <xstructured name="answer">{}</xstructured> B '
            '<xstructured name="label">{}</xstructured> C'
        )
        == "A  B  C"
    )
    assert (
        parser.strip_envelopes('A <xstructured name="answer">{"x": 1') == "A "
    )
