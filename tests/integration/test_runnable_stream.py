from __future__ import annotations

import re

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, AIMessageChunk

from tests.support import Answer, ChunkRunnable
from xstructured import (
    ParseError,
    RecoveryError,
    StreamEvent,
    StreamEventKind,
    XStructuredResult,
    with_xstructured_output,
)

Kind = StreamEventKind
SPLIT = ("Natural <xstr", 'uctured>{"val', 'ue": 42}</xstru', "ctured> tail")


def assert_protocol(
    events: list[StreamEvent[Answer]],
) -> XStructuredResult[Answer]:
    kinds = [event.kind for event in events]
    start, end = (
        kinds.index(Kind.STRUCTURED_START),
        kinds.index(Kind.STRUCTURED_END),
    )
    assert [event.sequence for event in events] == list(range(len(events)))
    assert set(kinds[:start]) <= {Kind.TEXT_DELTA}
    assert set(kinds[start + 1 : end]) <= {Kind.STRUCTURED_DELTA}
    assert set(kinds[end + 1 : -1]) <= {Kind.TEXT_DELTA}
    assert kinds[-1] is Kind.RESULT
    result = events[-1].result
    assert result is not None
    assert events[end].structured == result.structured
    text = "".join(
        event.text or "" for event in events if event.kind is Kind.TEXT_DELTA
    )
    assert text == result.content
    return result


def test_stream_yields_ordered_events_and_a_final_result() -> None:
    wrapper = with_xstructured_output(ChunkRunnable(SPLIT), Answer)

    result = assert_protocol(list(wrapper.stream("question")))

    assert result.structured == Answer(value=42)
    assert result.content == "Natural  tail"
    assert result.raw == "".join(SPLIT)
    assert result.metadata["envelope_count"] == 1


async def test_astream_matches_stream() -> None:
    wrapper = with_xstructured_output(ChunkRunnable(SPLIT), Answer)

    events = [event async for event in wrapper.astream("question")]

    assert [event.kind for event in events] == [
        event.kind for event in wrapper.stream("q")
    ]
    assert assert_protocol(events).structured == Answer(value=42)


def test_message_chunks_are_merged_into_the_raw_message() -> None:
    chunks = [
        AIMessageChunk(content="Hi <xstructured>", id="run-7"),
        AIMessageChunk(content='{"value": 1}</xstructured>'),
        AIMessageChunk(
            content=" bye",
            usage_metadata={
                "input_tokens": 4,
                "output_tokens": 6,
                "total_tokens": 10,
            },
        ),
    ]
    wrapper = with_xstructured_output(ChunkRunnable(chunks), Answer)

    result = assert_protocol(list(wrapper.stream("q")))

    assert isinstance(result.raw, AIMessage)
    assert result.raw.text == 'Hi <xstructured>{"value": 1}</xstructured> bye'
    assert result.metadata["message_id"] == "run-7"
    assert result.metadata["usage_metadata"]["total_tokens"] == 10


def test_chat_model_streams_produce_the_same_result_as_invoke() -> None:
    text = 'Here you go. <xstructured>{"value": 3}</xstructured> Anything else?'

    def model() -> GenericFakeChatModel:
        return GenericFakeChatModel(messages=iter([AIMessage(content=text)]))

    invoked = with_xstructured_output(model(), Answer).invoke("q")
    streamed = assert_protocol(
        list(with_xstructured_output(model(), Answer).stream("q"))
    )

    assert streamed.structured == invoked.structured
    assert streamed.content == invoked.content
    assert streamed.raw_text == invoked.raw_text


def test_stream_requires_a_complete_envelope() -> None:
    wrapper = with_xstructured_output(ChunkRunnable(["only prose"]), Answer)

    with pytest.raises(
        ParseError,
        match=re.escape("No <xstructured>...</xstructured> envelope"),
    ):
        list(wrapper.stream("q"))


def test_invalid_payloads_fail_when_the_envelope_closes() -> None:
    wrapper = with_xstructured_output(
        ChunkRunnable(
            ["Some prose first. ", '<xstructured>{"value": "x"}</xstructured>']
        ),
        Answer,
    )
    stream = wrapper.stream("q")

    assert next(stream).kind is Kind.TEXT_DELTA
    with pytest.raises(RecoveryError):
        next(stream)


def test_named_envelopes_cannot_be_streamed_directly() -> None:
    wrapper = with_xstructured_output(
        ChunkRunnable(["x"]), {"answer": Answer}, multiple_envelopes=True
    )

    with pytest.raises(ValueError, match="cannot be streamed"):
        list(wrapper.stream("q"))
