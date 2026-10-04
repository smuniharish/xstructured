"""Composition with other Runnables: downstream steps always receive the final result."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    RunnableGenerator,
    RunnableLambda,
    RunnableParallel,
)

from tests.support import Answer, ChunkRunnable, Recorder, reply
from xstructured import XStructuredResult, with_xstructured_output

ENVELOPED = 'Hi <xstructured>{"value": 4}</xstructured>'


def structured(result: XStructuredResult[Answer]) -> Answer:
    return result.structured


def test_downstream_steps_get_the_invoke_result_when_streaming() -> None:
    chain = with_xstructured_output(
        ChunkRunnable([ENVELOPED]), Answer
    ) | RunnableLambda(structured)

    assert chain.invoke("q") == Answer(value=4)
    assert list(chain.stream("q")) == [Answer(value=4)]


async def test_downstream_steps_get_the_invoke_result_when_async_streaming() -> (
    None
):
    chain = with_xstructured_output(
        ChunkRunnable([ENVELOPED]), Answer
    ) | RunnableLambda(structured)

    assert await chain.ainvoke("q") == Answer(value=4)
    assert [item async for item in chain.astream("q")] == [Answer(value=4)]


def test_streaming_named_envelopes_inside_a_chain_is_supported() -> None:
    wrapper = with_xstructured_output(
        ChunkRunnable(
            ['<xstructured name="answer">{"value": 2}</xstructured>']
        ),
        {"answer": Answer},
        multiple_envelopes=True,
    )

    [result] = list(
        (wrapper | RunnableLambda(lambda r: r.structured)).stream("q")
    )

    assert result == {"answer": Answer(value=2)}


def test_prompt_templates_compose_with_the_wrapper() -> None:
    recorder = Recorder(ENVELOPED)
    prompt = ChatPromptTemplate.from_messages(
        [("system", "You are terse."), ("human", "{question}")]
    )
    chain = prompt | with_xstructured_output(RunnableLambda(recorder), Answer)

    result = chain.invoke({"question": "What is four?"})

    assert result.structured == Answer(value=4)
    messages = recorder.inputs[0].to_messages()
    assert [m.type for m in messages] == ["system", "human"]
    assert messages[0].content.startswith("You are terse.\n\n")


def test_streamed_upstream_chunks_are_folded_into_one_input() -> None:
    def upstream(_: Iterator[str]) -> Iterator[str]:
        yield "first "
        yield "second"

    recorder = Recorder(ENVELOPED)
    chain = RunnableGenerator(upstream) | with_xstructured_output(
        RunnableLambda(recorder), Answer, inject_instructions=False
    )

    assert [r.structured for r in chain.stream("q")] == [Answer(value=4)]
    assert recorder.inputs == ["first second"]


async def test_async_upstream_chunks_are_folded_into_one_input() -> None:
    async def upstream(_: AsyncIterator[str]) -> AsyncIterator[str]:
        yield "first "
        yield "second"

    recorder = Recorder(ENVELOPED)
    chain = RunnableGenerator(upstream) | with_xstructured_output(
        RunnableLambda(recorder), Answer, inject_instructions=False
    )

    assert [r.structured async for r in chain.astream("q")] == [Answer(value=4)]
    assert recorder.inputs == ["first second"]


def test_unaddable_upstream_chunks_keep_the_last_chunk() -> None:
    def upstream(_: Iterator[str]) -> Iterator[object]:
        yield 1.5
        yield None

    recorder = Recorder(ENVELOPED)
    chain = RunnableGenerator(upstream) | with_xstructured_output(
        RunnableLambda(recorder), Answer, inject_instructions=False
    )

    list(chain.stream("q"))

    assert recorder.inputs == [None]


def test_empty_upstream_streams_produce_no_result() -> None:
    def upstream(_: Iterator[str]) -> Iterator[str]:
        yield from ()

    chain = RunnableGenerator(upstream) | with_xstructured_output(
        reply(ENVELOPED), Answer
    )

    assert list(chain.stream("q")) == []


async def test_empty_async_upstream_streams_produce_no_result() -> None:
    async def upstream(_: AsyncIterator[str]) -> AsyncIterator[str]:
        for item in ():
            yield item

    chain = RunnableGenerator(upstream) | with_xstructured_output(
        reply(ENVELOPED), Answer
    )

    assert [item async for item in chain.astream("q")] == []


def test_parallel_retry_fallback_and_config_bindings() -> None:
    wrapper = with_xstructured_output(reply(ENVELOPED), Answer)
    parallel = RunnableParallel(first=wrapper, second=wrapper)

    assert parallel.invoke("q")["first"].structured == Answer(value=4)
    streamed = next(chunk for chunk in parallel.stream("q") if "first" in chunk)
    assert streamed["first"].structured == Answer(value=4)
    assert wrapper.with_retry(stop_after_attempt=2).invoke(
        "q"
    ).structured == Answer(value=4)
    broken = with_xstructured_output(reply("no envelope"), Answer)
    assert broken.with_fallbacks([wrapper]).invoke("q").structured == Answer(
        value=4
    )
    assert wrapper.with_config(run_name="extract").invoke(
        "q"
    ).structured == Answer(value=4)
