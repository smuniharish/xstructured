"""Tests the extension templates must pass. Copy them with the templates.

The `*Contract` classes from `xstructured.testing` contribute one test per
promise the extension point makes; the end-to-end tests check the extension
inside a real wrapper with an offline `ScriptedChatModel`.
"""

from __future__ import annotations

import asyncio

import pytest
from decoder_template import LastLineFirst, PythonLiteralDecoder
from observer_template import MetricsObserver
from pydantic import BaseModel

from xstructured import ParseError, with_xstructured_output
from xstructured.testing import (
    JsonDecoderContract,
    ObserverContract,
    RecoveryStrategyContract,
    ScriptedChatModel,
)


class Answer(BaseModel):
    value: int
    label: str


class TestPythonLiteralDecoder(JsonDecoderContract):
    def make_decoder(self) -> PythonLiteralDecoder:
        return PythonLiteralDecoder()


class TestLastLineFirst(RecoveryStrategyContract):
    def make_strategy(self) -> LastLineFirst:
        return LastLineFirst()


class TestMetricsObserver(ObserverContract):
    def make_observer(self) -> MetricsObserver:
        return MetricsObserver()


def test_the_decoder_accepts_python_literals_inside_a_wrapper() -> None:
    reply = "Here. <xstructured>{'value': 7, 'label': 'seven'}</xstructured>"
    wrapper = with_xstructured_output(
        ScriptedChatModel.of(reply), Answer, decoder=PythonLiteralDecoder()
    )

    result = asyncio.run(wrapper.ainvoke("q"))

    assert result.structured == Answer(value=7, label="seven")
    assert result.json_text == '{"value": 7, "label": "seven"}'


def test_the_decoder_keeps_the_safety_rules() -> None:
    reply = '<xstructured>{"value": 1, "value": 2, "label": "x"}</xstructured>'
    wrapper = with_xstructured_output(
        ScriptedChatModel.of(reply), Answer, decoder=PythonLiteralDecoder()
    )

    with pytest.raises(ParseError, match="Duplicate JSON object key"):
        asyncio.run(wrapper.ainvoke("q"))


def test_the_strategy_finds_json_on_the_last_line() -> None:
    reply = (
        "<xstructured>The answer follows.\n"
        '{"value": 3, "label": "three"}</xstructured>'
    )
    wrapper = with_xstructured_output(
        ScriptedChatModel.of(reply), Answer, recovery=LastLineFirst()
    )

    result = asyncio.run(wrapper.ainvoke("q"))

    assert result.structured.value == 3
    assert result.recovered


def test_the_observer_counts_successes_and_failures() -> None:
    observer = MetricsObserver()
    good = with_xstructured_output(
        ScriptedChatModel.of(
            '<xstructured>{"value": 1, "label": "a"}</xstructured>'
        ),
        Answer,
        observer=observer,
    )
    bad = with_xstructured_output(
        ScriptedChatModel.of("no envelope"), Answer, observer=observer
    )

    asyncio.run(good.ainvoke("q"))
    with pytest.raises(ParseError):
        asyncio.run(bad.ainvoke("q"))

    assert observer.calls == {("invoke", "ok"): 1, ("invoke", "error"): 1}
    assert len(observer.durations) == len(observer.response_chars) == 1
