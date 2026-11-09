from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from tests.support import Answer
from xstructured import (
    MessageTextExtractor,
    StreamEventKind,
    with_xstructured_output,
)
from xstructured.testing import ScriptedChatModel

VALID = 'Done. <xstructured>{"value": 1}</xstructured>'


def graph(*responses: str) -> Any:
    return create_agent(ScriptedChatModel.of(*responses))


async def test_graphs_are_invoked_with_instructions_in_their_state() -> None:
    wrapper = with_xstructured_output(graph(VALID), Answer)

    result = await wrapper.ainvoke({"messages": [HumanMessage("q")]})

    assert result.structured == Answer(value=1)
    assert result.content == "Done. "
    assert result.raw["messages"][0].id == "xstructured-instructions"


async def test_graphs_stream_model_tokens() -> None:
    wrapper = with_xstructured_output(
        graph(VALID), Answer, extractor=MessageTextExtractor(nodes=["model"])
    )

    events = [e async for e in wrapper.astream({"messages": [("human", "q")]})]

    final = events[-1]
    assert final.kind is StreamEventKind.RESULT
    assert final.result is not None
    assert final.result.structured == Answer(value=1)
    assert final.result.raw_text == VALID


def test_explicit_stream_modes_are_kept() -> None:
    wrapper = with_xstructured_output(graph(VALID), Answer)

    results = list(
        wrapper.transform(
            iter([{"messages": [("human", "q")]}]), stream_mode="messages"
        )
    )

    assert results[0].structured == Answer(value=1)
