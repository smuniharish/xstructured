"""Opt-in, bounded LLM-assisted repair. The "repair model" is a plain RunnableLambda."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from tests.support import Answer, Recorder, reply
from xstructured import (
    LimitExceededError,
    ParseError,
    ParserConfig,
    RecoveryError,
    RepairConfig,
    RepairError,
    with_xstructured_output,
)

MALFORMED = "Sure. <xstructured>{value: 42}</xstructured> Thanks!"
FIXED = '<xstructured>{"value": 42}</xstructured>'


def test_repair_is_never_called_unless_configured() -> None:
    with pytest.raises(RecoveryError):
        with_xstructured_output(reply(MALFORMED), Answer).invoke("q")


def test_repair_fixes_a_response_recovery_could_not() -> None:
    repair = Recorder(FIXED)
    wrapper = with_xstructured_output(
        reply(MALFORMED), Answer, repair=RunnableLambda(repair)
    )

    result = wrapper.invoke("q")

    assert result.structured == Answer(value=42)
    assert result.repaired
    assert result.repair_attempts == 1
    assert result.content == "Sure.  Thanks!"
    assert result.raw_text == MALFORMED
    [prompt] = repair.inputs
    assert "Problems (attempt 1 of 1):" in prompt
    assert "- Expecting property name enclosed in double quotes" in prompt
    assert wrapper.instructions in prompt
    assert prompt.endswith(f"Response to correct:\n{MALFORMED}")


def test_repair_accepts_message_output() -> None:
    wrapper = with_xstructured_output(
        reply(MALFORMED), Answer, repair=reply(AIMessage(content=FIXED))
    )

    assert wrapper.invoke("q").structured == Answer(value=42)


def test_repair_retries_with_the_latest_failure_then_gives_up() -> None:
    repair = Recorder(
        "<xstructured>{value: 1}</xstructured>", "still no envelope"
    )
    wrapper = with_xstructured_output(
        reply(MALFORMED),
        Answer,
        repair=RunnableLambda(repair),
        repair_config=RepairConfig(max_attempts=3),
    )

    with pytest.raises(RepairError) as excinfo:
        wrapper.invoke("q")

    error = excinfo.value
    assert len(repair.inputs) == 3
    assert "Problems (attempt 3 of 3):" in repair.inputs[2]
    assert repair.inputs[2].endswith("Response to correct:\nstill no envelope")
    assert error.attempts == 3
    assert len(error.failures) == 3
    assert "No complete <xstructured>" in error.failures[-1]
    assert error.text == MALFORMED
    assert isinstance(error.__cause__, ParseError)
    assert "3 attempt(s)" in str(error)


def test_repair_can_be_disabled_by_configuration() -> None:
    def must_not_run(_: object) -> str:
        raise AssertionError("repair must not run")

    wrapper = with_xstructured_output(
        reply(MALFORMED),
        Answer,
        repair=RunnableLambda(must_not_run),
        repair_config=RepairConfig(enabled=False),
    )

    with pytest.raises(RecoveryError):
        wrapper.invoke("q")


def test_limit_violations_are_never_repaired() -> None:
    def must_not_run(_: object) -> str:
        raise AssertionError("repair must not run")

    wrapper = with_xstructured_output(
        reply("x" * 50),
        Answer,
        parser_config=ParserConfig(max_input_chars=10),
        repair=RunnableLambda(must_not_run),
    )

    with pytest.raises(LimitExceededError):
        wrapper.invoke("q")


def test_valid_responses_never_touch_the_repair_runnable() -> None:
    repair = Recorder(FIXED)
    wrapper = with_xstructured_output(
        reply(FIXED), Answer, repair=RunnableLambda(repair)
    )

    assert not wrapper.invoke("q").repaired
    assert repair.inputs == []


async def test_async_repair() -> None:
    repair = Recorder(FIXED)
    wrapper = with_xstructured_output(
        reply(MALFORMED),
        Answer,
        repair=RunnableLambda(repair.__call__, afunc=repair.acall),
    )

    result = await wrapper.ainvoke("q")

    assert result.structured == Answer(value=42)
    assert result.repaired


async def test_async_repair_gives_up_after_the_budget() -> None:
    repair = Recorder("nope")
    wrapper = with_xstructured_output(
        reply(MALFORMED),
        Answer,
        repair=RunnableLambda(repair.__call__, afunc=repair.acall),
    )

    with pytest.raises(RepairError):
        await wrapper.ainvoke("q")


def test_repair_also_applies_inside_composed_streams() -> None:
    wrapper = with_xstructured_output(
        reply(MALFORMED), Answer, repair=reply(FIXED)
    )
    chain = wrapper | RunnableLambda(lambda result: result.repaired)

    assert list(chain.stream("q")) == [True]


async def test_repair_also_applies_inside_composed_async_streams() -> None:
    wrapper = with_xstructured_output(
        reply(MALFORMED), Answer, repair=reply(FIXED)
    )
    chain = wrapper | RunnableLambda(lambda result: result.repaired)

    assert [item async for item in chain.astream("q")] == [True]
