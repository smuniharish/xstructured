"""Offline tests for structured output with xstructured.

Copy this file into the project's tests, replace `Ticket` with the real
schema and the scripted replies with realistic model answers, and make
`make_triage` build the wrapper the way the application does.
`ScriptedChatModel` replays the replies in order, so the tests need no network
or credentials. The calls are async and run through `asyncio.run`, so plain
pytest is enough.
"""

from __future__ import annotations

import asyncio
from typing import Literal

import pytest
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

from xstructured import (
    ParseError,
    RepairConfig,
    StreamEventKind,
    XStructuredRunnable,
    with_xstructured_output,
)
from xstructured.testing import ScriptedChatModel


class Ticket(BaseModel):
    priority: Literal["low", "high", "critical"] = Field(
        description="How urgent the request is."
    )
    team: str
    summary: str


VALID = (
    "Checkout is down in the EU, so this is critical. <xstructured>"
    '{"priority": "critical", "team": "payments", '
    '"summary": "EU checkout outage"}</xstructured>'
)
INVALID = (
    '<xstructured>{"priority": "urgent", "team": "payments"}</xstructured>'
)


def make_triage(
    model: ScriptedChatModel, *, repair: bool = False
) -> XStructuredRunnable:
    """Build the wrapper exactly as the application does."""
    if repair:
        return with_xstructured_output(
            model,
            Ticket,
            repair=model,
            repair_config=RepairConfig(max_attempts=1),
        )
    return with_xstructured_output(model, Ticket)


def test_returns_prose_and_a_validated_value() -> None:
    result = asyncio.run(
        make_triage(ScriptedChatModel.of(VALID)).ainvoke("EU checkout is down")
    )

    assert result.structured.priority == "critical"
    assert result.content.startswith("Checkout is down")
    assert "<xstructured>" not in result.content
    assert not result.recovered


def test_invalid_output_raises_parse_error_without_leaking_it() -> None:
    with pytest.raises(ParseError) as caught:
        asyncio.run(
            make_triage(ScriptedChatModel.of(INVALID)).ainvoke(
                "EU checkout is down"
            )
        )

    assert caught.value.text == INVALID
    assert INVALID not in str(caught.value)


def test_bounded_repair_fixes_one_invalid_reply() -> None:
    result = asyncio.run(
        make_triage(ScriptedChatModel.of(INVALID, VALID), repair=True).ainvoke(
            "EU checkout is down"
        )
    )

    assert result.repaired
    assert result.repair_attempts == 1
    assert result.structured.team == "payments"


def test_streams_prose_before_the_structured_value() -> None:
    async def kinds() -> list[StreamEventKind]:
        wrapper = make_triage(ScriptedChatModel.of(VALID))
        return [event.kind async for event in wrapper.astream("EU checkout")]

    events = asyncio.run(kinds())

    assert events[0] is StreamEventKind.TEXT_DELTA
    assert events.index(StreamEventKind.STRUCTURED_START) < events.index(
        StreamEventKind.STRUCTURED_END
    )
    assert events[-1] is StreamEventKind.RESULT


def test_agent_middleware_keeps_tools_and_validates_the_final_answer() -> None:
    agents = pytest.importorskip("langchain.agents")
    from langchain_core.tools import tool

    from xstructured.agents import XStructuredMiddleware

    @tool
    def owner(service: str) -> str:
        """Return the team that owns a service."""
        return "payments"

    model = ScriptedChatModel.of(
        AIMessage(
            content="",
            tool_calls=[
                {"name": "owner", "args": {"service": "checkout"}, "id": "1"}
            ],
        ),
        VALID,
    )
    agent = agents.create_agent(
        model, tools=[owner], middleware=[XStructuredMiddleware(Ticket)]
    )
    state = asyncio.run(
        agent.ainvoke({"messages": [("human", "Checkout is down")]})
    )

    assert state["structured_response"].structured.team == "payments"
    assert [message.type for message in state["messages"]] == [
        "human",
        "ai",
        "tool",
        "ai",
    ]
