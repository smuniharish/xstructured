from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import BaseModel

from xstructured import XStructuredResult, with_xstructured_output


class Answer(BaseModel):
    value: int


class Label(BaseModel):
    name: str


def response_for(value: str) -> AIMessage:
    assert "<xstructured>" in value
    return AIMessage(
        content='The answer is 42. <xstructured>{"value": 42}</xstructured>',
        id="message-1",
        response_metadata={"model": "fake-model"},
    )


def test_invoke_is_composable_and_preserves_raw_message() -> None:
    runnable = with_xstructured_output(RunnableLambda(response_for), Answer)
    pipeline = RunnableLambda(lambda value: f"Question: {value}") | runnable

    result = pipeline.invoke("six times seven")

    assert isinstance(runnable, Runnable)
    assert result.content == "The answer is 42. "
    assert result.structured == Answer(value=42)
    assert isinstance(result.raw, AIMessage)
    assert result.raw.id == "message-1"
    assert result.metadata["response_metadata"] == {"model": "fake-model"}
    assert result.metadata["schema_fingerprint"] == runnable.schema_fingerprint
    assert result.metadata["envelope_detected"] is True
    assert result.metadata["envelope_count"] == 1
    assert result.metadata["parse_duration"] >= 0
    assert result.metadata["repair_attempted"] is False
    assert result.metadata["repair_attempt_count"] == 0
    assert result.metadata["stream_completed"] is True


@pytest.mark.asyncio
async def test_ainvoke_uses_wrapped_async_semantics() -> None:
    seen: list[str] = []

    async def respond(value: str) -> str:
        seen.append(value)
        return 'Done. <xstructured>{"value": 7}</xstructured>'

    runnable = with_xstructured_output(RunnableLambda(respond), Answer)
    result = await runnable.ainvoke("calculate")

    assert result.structured.value == 7
    assert runnable.instructions in seen[0]


def test_batch_uses_native_runnable_semantics() -> None:
    def respond(value: str) -> str:
        number = 1 if "one" in value else 2
        return f'<xstructured>{{"value": {number}}}</xstructured>'

    runnable = with_xstructured_output(RunnableLambda(respond), Answer)

    results = runnable.batch(["one", "two"], config={"max_concurrency": 2})

    assert [result.structured.value for result in results] == [1, 2]


@pytest.mark.asyncio
async def test_abatch_uses_native_runnable_semantics() -> None:
    async def respond(value: str) -> str:
        number = 3 if "three" in value else 4
        return f'<xstructured>{{"value": {number}}}</xstructured>'

    runnable = with_xstructured_output(RunnableLambda(respond), Answer)

    results = await runnable.abatch(
        ["three", "four"],
        config={"max_concurrency": 2},
    )

    assert [result.structured.value for result in results] == [3, 4]


def test_message_inputs_receive_a_system_instruction() -> None:
    def respond(messages: list[BaseMessage]) -> str:
        assert messages[0].type == "system"
        assert "<xstructured>" in str(messages[0].content)
        return '<xstructured>{"value": 9}</xstructured>'

    runnable = with_xstructured_output(RunnableLambda(respond), Answer)

    result = runnable.invoke([AIMessage(content="question")])

    assert result.structured.value == 9


def test_raw_string_output_is_supported() -> None:
    runnable = with_xstructured_output(
        RunnableLambda(lambda _: '<xstructured>{"value": 11}</xstructured>'),
        Answer,
    )
    result = runnable.invoke("question")

    assert isinstance(result, XStructuredResult)
    assert result.raw == '<xstructured>{"value": 11}</xstructured>'


def test_multiple_named_payloads_are_validated_and_instructions_are_explicit() -> None:
    def respond(value: str) -> str:
        assert "JSON array" in value
        assert '"schema": "<name>"' in value
        return (
            '<xstructured>['
            '{"schema":"answer","payload":{"value":11}},'
            '{"schema":"label","payload":{"name":"ready"}}'
            "]</xstructured>"
        )

    runnable = with_xstructured_output(
        RunnableLambda(respond),
        {"answer": Answer, "label": Label},
        multiple=True,
    )

    result = runnable.invoke("classify this")

    assert result.structured == [Answer(value=11), Label(name="ready")]
