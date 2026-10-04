"""The wrapper is a traced LangChain run with the wrapped Runnable as a child run."""

from __future__ import annotations

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from tests.support import Answer, RunLog
from xstructured import StreamEvent, XStructuredResult, with_xstructured_output

ENVELOPED = 'Hi <xstructured>{"value": 4}</xstructured>'


def answer(_: object) -> str:
    return ENVELOPED


def fix(_: object) -> str:
    return ENVELOPED


def test_invoke_creates_a_parent_run_for_the_wrapper() -> None:
    log = RunLog()
    wrapper = with_xstructured_output(RunnableLambda(answer), Answer)

    result = wrapper.invoke(
        "q", config={"callbacks": [log], "run_name": "extract"}
    )

    parent = log.by_name("extract")
    child = log.by_name("answer")
    assert parent["parent_run_id"] is None
    assert child["parent_run_id"] == parent["run_id"]
    assert log.ends[-1] is result


async def test_ainvoke_creates_a_parent_run_for_the_wrapper() -> None:
    log = RunLog()
    wrapper = with_xstructured_output(RunnableLambda(answer), Answer)

    await wrapper.ainvoke("q", config={"callbacks": [log]})

    assert (
        log.by_name("answer")["parent_run_id"]
        == log.by_name("XStructuredRunnable")["run_id"]
    )


def test_stream_creates_a_parent_run_for_the_wrapper() -> None:
    log = RunLog()
    wrapper = with_xstructured_output(RunnableLambda(answer), Answer)

    events = list(wrapper.stream("q", config={"callbacks": [log]}))

    parent = log.by_name("XStructuredRunnable")
    assert log.by_name("answer")["parent_run_id"] == parent["run_id"]
    assert log.ends[-1] is events[-1]


def test_repair_runs_are_tagged_children_of_the_wrapper() -> None:
    log = RunLog()
    wrapper = with_xstructured_output(
        RunnableLambda(lambda _: "broken"), Answer, repair=RunnableLambda(fix)
    )

    wrapper.invoke("q", config={"callbacks": [log]})

    repair = log.by_name("fix")
    assert (
        repair["parent_run_id"] == log.by_name("XStructuredRunnable")["run_id"]
    )
    assert "xstructured:repair" in repair["tags"]


async def test_astream_events_include_protocol_events_and_model_tokens() -> (
    None
):
    model = GenericFakeChatModel(messages=iter([AIMessage(content=ENVELOPED)]))
    wrapper = with_xstructured_output(model, Answer)

    events = [
        event async for event in wrapper.astream_events("q", version="v2")
    ]

    names = {(event["event"], event["name"]) for event in events}
    assert ("on_chain_start", "XStructuredRunnable") in names
    assert ("on_chat_model_stream", "GenericFakeChatModel") in names
    streamed = [
        event["data"]["chunk"]
        for event in events
        if event["event"] == "on_chain_stream"
        and event["name"] == "XStructuredRunnable"
    ]
    assert all(isinstance(chunk, StreamEvent) for chunk in streamed)
    final = streamed[-1].result
    assert isinstance(final, XStructuredResult)
    assert final.structured == Answer(value=4)
