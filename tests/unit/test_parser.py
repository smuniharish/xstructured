import pytest
from pydantic import BaseModel

from xstructured.core import EnvelopeError, ParseError, ParserConfig, RecoveryError
from xstructured.envelope import EnvelopeSpec
from xstructured.parser import StructuredParser


class Answer(BaseModel):
    value: int


def test_parser_validates_json_against_pydantic_schema() -> None:
    result = StructuredParser(Answer).parse('{"value": 42}')

    assert result.value == Answer(value=42)
    assert not result.recovered


def test_parser_recovers_json_fence_and_surrounding_text() -> None:
    result = StructuredParser(Answer).parse('Here:\n```json\n{"value": 5}\n```\n')

    assert result.value.value == 5
    assert result.recovered


def test_parser_extracts_required_envelope() -> None:
    parser = StructuredParser(
        Answer,
        envelope=EnvelopeSpec("<result>", "</result>"),
        config=ParserConfig(require_envelope=True),
    )

    result = parser.parse('ignore <result>{"value": 7}</result> ignore')

    assert result.value.value == 7
    assert result.envelope_found


def test_parser_rejects_missing_required_envelope() -> None:
    parser = StructuredParser(
        Answer,
        envelope=EnvelopeSpec("<result>", "</result>"),
        config=ParserConfig(require_envelope=True),
    )

    with pytest.raises(ParseError, match="No complete envelope"):
        parser.parse('{"value": 7}')


def test_parser_reports_recovery_failure() -> None:
    with pytest.raises(RecoveryError):
        StructuredParser(Answer).parse('{"value": "nope"}')


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ('{"value": NaN}', "Non-standard JSON constant"),
        ('{"value": 1, "value": 2}', "Duplicate JSON object key"),
        ('{"value": [[[[1]]]]}', "JSON nesting exceeds"),
    ],
)
def test_parser_rejects_adversarial_json(payload: str, message: str) -> None:
    config = ParserConfig(
        recovery={"enabled": False},
        max_nesting_depth=3,
    )

    with pytest.raises(ParseError, match=message):
        StructuredParser(Answer, config=config).parse(payload)


def test_parser_enforces_payload_limit_after_envelope_extraction() -> None:
    parser = StructuredParser(
        Answer,
        envelope=EnvelopeSpec("<result>", "</result>"),
        config=ParserConfig(
            require_envelope=True,
            max_payload_chars=10,
            recovery={"enabled": False},
        ),
    )

    with pytest.raises(EnvelopeError, match="payload exceeds"):
        parser.parse('<result>{"value": 42}</result>')
