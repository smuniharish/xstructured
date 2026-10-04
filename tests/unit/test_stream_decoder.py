from __future__ import annotations

import pytest

from tests.support import Answer
from xstructured import (
    EnvelopeSpec,
    LimitExceededError,
    ParseError,
    ParserConfig,
    RecoveryError,
    StreamDecoder,
    StreamEvent,
    StreamEventKind,
    StructuredParser,
)

Kind = StreamEventKind


def decode(
    chunks: list[str], parser: StructuredParser[Answer] | None = None
) -> list[StreamEvent[Answer]]:
    decoder = StreamDecoder(parser or StructuredParser(Answer))
    events: list[StreamEvent[Answer]] = []
    for chunk in chunks:
        events.extend(decoder.feed(chunk))
    decoder.finalize()
    return events


def test_events_are_ordered_across_split_delimiters() -> None:
    events = decode(
        ["Natural <xstr", 'uctured>{"val', 'ue": 42}</xstru', "ctured> tail"]
    )

    assert [event.sequence for event in events] == list(range(len(events)))
    assert [event.kind for event in events] == [
        Kind.TEXT_DELTA,
        Kind.TEXT_DELTA,
        Kind.STRUCTURED_START,
        Kind.STRUCTURED_DELTA,
        Kind.STRUCTURED_DELTA,
        Kind.STRUCTURED_END,
        Kind.TEXT_DELTA,
    ]
    assert (
        "".join(e.text or "" for e in events if e.kind is Kind.TEXT_DELTA)
        == "Natural  tail"
    )
    assert (
        "".join(e.text or "" for e in events if e.kind is Kind.STRUCTURED_DELTA)
        == '{"value": 42}'
    )
    assert events[5].structured == Answer(value=42)


def test_decoder_exposes_text_payload_and_result() -> None:
    decoder = StreamDecoder(StructuredParser(Answer))
    decoder.feed('Hi <xstructured>```json\n{"value": 1}\n```</xstructured>!')
    decoder.finalize()

    assert decoder.complete
    assert decoder.text == "Hi !"
    assert decoder.payload == '```json\n{"value": 1}\n```'
    assert decoder.result.value == Answer(value=1)
    assert decoder.result.recovered
    assert decoder.next_sequence == 5


def test_result_is_unavailable_before_the_envelope_completes() -> None:
    decoder = StreamDecoder(StructuredParser(Answer))
    decoder.feed("<xstructured>{")

    with pytest.raises(ParseError, match="No complete envelope"):
        _ = decoder.result


def test_the_parser_envelope_is_used() -> None:
    parser = StructuredParser(Answer, envelope=EnvelopeSpec("[[", "]]"))

    events = decode(['a [[{"value": 3}]] b'], parser)

    assert events[2].text == '{"value": 3}'
    assert events[3].structured == Answer(value=3)


def test_missing_envelope_fails_at_finalize_with_the_text() -> None:
    decoder = StreamDecoder(StructuredParser(Answer))
    decoder.feed("only prose <xs")

    with pytest.raises(
        ParseError, match=r"No <xstructured>\.\.\.</xstructured> envelope"
    ) as excinfo:
        decoder.finalize()

    assert excinfo.value.text == "only prose <xs"


def test_unterminated_envelope_fails_at_finalize() -> None:
    decoder = StreamDecoder(StructuredParser(Answer))
    decoder.feed('pre <xstructured>{"value": 1}')

    with pytest.raises(
        ParseError, match="was not closed with </xstructured>"
    ) as excinfo:
        decoder.finalize()

    assert excinfo.value.text == 'pre <xstructured>{"value": 1}'


def test_invalid_payload_fails_when_the_envelope_closes() -> None:
    decoder = StreamDecoder(StructuredParser(Answer))

    with pytest.raises(RecoveryError):
        decoder.feed('<xstructured>{"value": "x"}</xstructured>')


def test_limits_are_enforced_while_streaming() -> None:
    small_input = StructuredParser(
        Answer, config=ParserConfig(max_input_chars=10)
    )
    small_payload = StructuredParser(
        Answer, config=ParserConfig(max_payload_chars=5)
    )

    with pytest.raises(
        LimitExceededError, match="Stream input exceeds"
    ) as excinfo:
        decode(["<xstructured>", '{"value": 1}'], small_input)
    assert excinfo.value.limit == "max_input_chars"
    with pytest.raises(LimitExceededError, match="payload exceeds"):
        decode(['<xstructured>{"value": 12345}'], small_payload)


def test_named_envelopes_cannot_be_streamed() -> None:
    with pytest.raises(ValueError, match="cannot be streamed"):
        StreamDecoder(StructuredParser({"a": Answer}, multiple_envelopes=True))


def test_chunks_must_be_strings() -> None:
    with pytest.raises(TypeError, match="strings"):
        StreamDecoder(StructuredParser(Answer)).feed(1)  # type: ignore[arg-type]


def test_empty_chunks_produce_no_events() -> None:
    assert StreamDecoder(StructuredParser(Answer)).feed("") == []
