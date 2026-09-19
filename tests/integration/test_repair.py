"""Optional, bounded LLM-assisted repair for the LangChain integration.

No network calls: the "repair model" here is a plain RunnableLambda, just
like the wrapped model in the other integration tests.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

from xstructured import RepairConfig, with_xstructured_output
from xstructured.core import RecoveryError, RepairError


class Answer(BaseModel):
    value: int


def _malformed_response(_: object) -> str:
    # An unquoted object key: invalid JSON that conservative recovery cannot fix.
    return "Sure. <xstructured>{value: 42}</xstructured>"


def test_repair_is_not_invoked_when_not_configured() -> None:
    runnable = with_xstructured_output(RunnableLambda(_malformed_response), Answer)

    with pytest.raises(RecoveryError):
        runnable.invoke("q")


def test_repair_fixes_a_response_recovery_could_not() -> None:
    calls: list[str] = []

    def fix(prompt: str) -> str:
        calls.append(prompt)
        return '<xstructured>{"value": 42}</xstructured>'

    runnable = with_xstructured_output(
        RunnableLambda(_malformed_response),
        Answer,
        repair=RunnableLambda(fix),
    )

    result = runnable.invoke("q")

    assert result.structured == Answer(value=42)
    assert result.repaired is True
    assert result.repair_attempt_count == 1
    assert result.metadata["repair_attempted"] is True
    assert result.metadata["repair_attempt_count"] == 1
    assert len(calls) == 1
    assert "Repair attempt 1 of 1" in calls[0]
    assert "Invalid response:" in calls[0]


def test_repair_accepts_message_output_from_the_repair_runnable() -> None:
    def fix(_: str) -> AIMessage:
        return AIMessage(content='<xstructured>{"value": 7}</xstructured>')

    runnable = with_xstructured_output(
        RunnableLambda(_malformed_response),
        Answer,
        repair=RunnableLambda(fix),
    )

    result = runnable.invoke("q")

    assert result.structured == Answer(value=7)
    assert result.repaired is True


@pytest.mark.asyncio
async def test_arepair_is_used_for_ainvoke() -> None:
    calls: list[str] = []

    async def fix(prompt: str) -> str:
        calls.append(prompt)
        return '<xstructured>{"value": 9}</xstructured>'

    runnable = with_xstructured_output(
        RunnableLambda(_malformed_response),
        Answer,
        repair=RunnableLambda(fix),
    )

    result = await runnable.ainvoke("q")

    assert result.structured == Answer(value=9)
    assert result.repaired is True
    assert len(calls) == 1


def test_repair_retries_up_to_the_configured_bound_then_raises() -> None:
    attempts: list[str] = []

    def still_bad(prompt: str) -> str:
        attempts.append(prompt)
        return "<xstructured>{value: still bad}</xstructured>"

    runnable = with_xstructured_output(
        RunnableLambda(_malformed_response),
        Answer,
        repair=RunnableLambda(still_bad),
        repair_config=RepairConfig(max_attempts=3),
    )

    with pytest.raises(RepairError) as excinfo:
        runnable.invoke("q")

    assert len(attempts) == 3
    assert "Repair attempt 1 of 3" in attempts[0]
    assert "Repair attempt 3 of 3" in attempts[2]
    assert excinfo.value.attempt_count == 3
    assert excinfo.value.repair_errors


def test_repair_config_can_disable_repair_without_removing_the_runnable() -> None:
    def fix(_: str) -> str:
        raise AssertionError("repair Runnable must not be invoked when disabled")

    runnable = with_xstructured_output(
        RunnableLambda(_malformed_response),
        Answer,
        repair=RunnableLambda(fix),
        repair_config=RepairConfig(enabled=False),
    )

    with pytest.raises(RecoveryError):
        runnable.invoke("q")


def test_successful_first_parse_never_touches_the_repair_runnable() -> None:
    def fix(_: str) -> str:
        raise AssertionError("repair Runnable must not be invoked on a valid response")

    def good_response(_: object) -> str:
        return '<xstructured>{"value": 1}</xstructured>'

    runnable = with_xstructured_output(
        RunnableLambda(good_response),
        Answer,
        repair=RunnableLambda(fix),
    )

    result = runnable.invoke("q")

    assert result.structured == Answer(value=1)
    assert result.repaired is False
