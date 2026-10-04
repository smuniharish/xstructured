"""Static typing contract of the public API, checked by pyrefly (and executed by pytest)."""

from __future__ import annotations

from typing import Any, assert_type

from langchain_core.runnables import RunnableLambda
from pydantic import TypeAdapter

from tests.support import Answer
from xstructured import (
    ParseResult,
    StreamEvent,
    StructuredParser,
    XStructuredResult,
    XStructuredRunnable,
    with_xstructured_output,
)

ENVELOPED = '<xstructured>{"value": 1}</xstructured>'


def respond(question: str) -> str:
    return ENVELOPED


def test_parser_value_types_follow_the_schema() -> None:
    assert_type(StructuredParser(Answer), StructuredParser[Answer])
    assert_type(
        StructuredParser(Answer, multiple=True), StructuredParser[list[Answer]]
    )
    assert_type(StructuredParser(TypeAdapter(int)), StructuredParser[int])
    assert_type(
        StructuredParser(TypeAdapter(int), multiple=True),
        StructuredParser[list[int]],
    )
    assert_type(
        StructuredParser({"answer": Answer}, multiple_envelopes=True),
        StructuredParser[dict[str, Any]],
    )
    assert_type(StructuredParser({"answer": Answer}), StructuredParser[Any])
    assert_type(
        StructuredParser(Answer).parse('{"value": 1}'), ParseResult[Answer]
    )


def test_wrapper_types_follow_the_input_and_schema() -> None:
    runnable = RunnableLambda(respond)

    wrapper = with_xstructured_output(runnable, Answer)
    assert_type(wrapper, XStructuredRunnable[str, Answer])
    assert_type(wrapper.invoke("q"), XStructuredResult[Answer])
    assert_type(wrapper.invoke("q").structured, Answer)
    assert_type(next(iter(wrapper.stream("q"))), StreamEvent[Answer])

    many = with_xstructured_output(runnable, Answer, multiple=False)
    assert_type(many, XStructuredRunnable[str, Answer])
    assert_type(
        with_xstructured_output(
            RunnableLambda(lambda _: "<xstructured>[]</xstructured>"),
            Answer,
            multiple=True,
        ),
        XStructuredRunnable[Any, list[Answer]],
    )
    assert_type(
        with_xstructured_output(runnable, TypeAdapter(int)),
        XStructuredRunnable[str, int],
    )
    assert_type(
        with_xstructured_output(
            runnable, {"answer": Answer}, multiple_envelopes=True
        ),
        XStructuredRunnable[str, dict[str, Any]],
    )
    assert_type(
        with_xstructured_output(runnable, {"answer": Answer}),
        XStructuredRunnable[str, Any],
    )
