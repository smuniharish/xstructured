from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel

from xstructured import EnvelopeSpec, StreamDecoder
from xstructured.core import ParseError, ParserConfig
from xstructured.parser import StructuredParser


class TextAnswer(BaseModel):
    value: str


@given(
    value=st.text(),
    boundaries=st.lists(st.integers(min_value=1, max_value=8), min_size=1, max_size=30),
)
def test_stream_decoder_handles_arbitrary_chunk_boundaries(
    value: str, boundaries: list[int]
) -> None:
    envelope = EnvelopeSpec("<x>", "</x>")
    document = envelope.wrap(TextAnswer(value=value).model_dump_json())
    chunks: list[str] = []
    offset = 0
    for width in boundaries:
        if offset >= len(document):
            break
        chunks.append(document[offset : offset + width])
        offset += width
    if offset < len(document):
        chunks.append(document[offset:])

    decoder = StreamDecoder(StructuredParser(TextAnswer), envelope)
    for chunk in chunks:
        decoder.feed(chunk)
    decoder.finalize()

    assert decoder.complete
    assert decoder.payload == TextAnswer(value=value).model_dump_json()


@given(value=st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=100))
def test_delimiter_like_unicode_in_json_strings_does_not_end_envelope(value: str) -> None:
    envelope = EnvelopeSpec("[[", "]]")
    payload = TextAnswer(value=f"{value} ]] {value}").model_dump_json()
    decoder = StreamDecoder(StructuredParser(TextAnswer), envelope)

    decoder.feed(envelope.start + payload[: len(payload) // 2])
    decoder.feed(payload[len(payload) // 2 :] + envelope.end)

    assert decoder.complete
    assert decoder.payload == payload


def test_stream_decoder_rejects_oversized_payload_without_completion() -> None:
    decoder = StreamDecoder(
        StructuredParser(
            TextAnswer,
            config=ParserConfig(max_payload_chars=10),
        ),
        EnvelopeSpec("<x>", "</x>"),
    )

    with pytest.raises(ParseError, match="Stream payload exceeds"):
        decoder.feed('<x>{"value":"1234567890"}')
