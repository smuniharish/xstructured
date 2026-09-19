from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from xstructured import (
    StreamEventKind,
    XStructuredResult,
    with_xstructured_output,
)


class Answer(BaseModel):
    value: int


class ChunkRunnable(Runnable[str, str]):
    def invoke(self, input: str, config=None, **kwargs) -> str:  # noqa: A002
        return "".join(self._chunks())

    def stream(
        self,
        input: str,  # noqa: A002
        config=None,
        **kwargs,
    ) -> Iterator[str]:
        yield from self._chunks()

    async def astream(
        self,
        input: str,  # noqa: A002
        config=None,
        **kwargs,
    ) -> AsyncIterator[str]:
        for chunk in self._chunks():
            yield chunk

    @staticmethod
    def _chunks() -> tuple[str, ...]:
        return (
            "Natural <xstr",
            'uctured>{"val',
            'ue": 42}</xstru',
            "ctured> tail",
        )


def assert_ordered_stream(events: list) -> None:
    assert [event.sequence for event in events] == list(range(len(events)))
    kinds = [event.kind for event in events]
    start_index = kinds.index(StreamEventKind.STRUCTURED_START)
    end_index = kinds.index(StreamEventKind.STRUCTURED_END)
    assert all(kind is StreamEventKind.TEXT_DELTA for kind in kinds[:start_index])
    assert all(
        kind is StreamEventKind.STRUCTURED_DELTA for kind in kinds[start_index + 1 : end_index]
    )
    assert all(kind is StreamEventKind.TEXT_DELTA for kind in kinds[end_index + 1 : -1])
    assert kinds[-1] is StreamEventKind.RESULT
    assert (
        "".join(event.text or "" for event in events if event.kind is StreamEventKind.TEXT_DELTA)
        == "Natural  tail"
    )
    assert (
        "".join(
            event.text or "" for event in events if event.kind is StreamEventKind.STRUCTURED_DELTA
        )
        == '{"value": 42}'
    )
    assert isinstance(events[-1].result, XStructuredResult)
    assert events[-1].result.structured == Answer(value=42)


def test_stream_orders_events_across_split_delimiters() -> None:
    runnable = with_xstructured_output(ChunkRunnable(), Answer)

    assert_ordered_stream(list(runnable.stream("question")))


def test_stream_ignores_closing_delimiter_inside_json_string() -> None:
    class StringAnswer(BaseModel):
        value: str

    class EmbeddedDelimiterRunnable(ChunkRunnable):
        @staticmethod
        def _chunks() -> tuple[str, ...]:
            return (
                '<xstructured>{"value": "literal </xstr',
                'uctured> text"}</xstructured>',
            )

    runnable = with_xstructured_output(
        EmbeddedDelimiterRunnable(),
        StringAnswer,
    )
    events = list(runnable.stream("q"))

    assert events[-1].result.structured.value == "literal </xstructured> text"


@pytest.mark.asyncio
async def test_astream_matches_sync_event_order() -> None:
    runnable = with_xstructured_output(ChunkRunnable(), Answer)

    events = [event async for event in runnable.astream("question")]

    assert_ordered_stream(events)
