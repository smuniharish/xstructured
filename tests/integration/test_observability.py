from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import Any, cast, override

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import StatusCode
from pydantic import BaseModel, ValidationInfo, field_validator

from tests.support import Answer, Recorder, RecordingObserver, reply
from xstructured import (
    CONTEXT_KEY,
    MessageInstructionInjector,
    MessageTextExtractor,
    ParseError,
    RepairConfig,
    RepairPromptBuilder,
    with_xstructured_output,
)
from xstructured.otel import OpenTelemetryObserver
from xstructured.testing import ObserverContract

VALID = '<xstructured>{"value": 1}</xstructured>'
INVALID = "<xstructured>{}</xstructured>"


class Limited(BaseModel):
    value: int

    @field_validator("value")
    @classmethod
    def within_limit(cls, value: int, info: ValidationInfo) -> int:
        limit = (info.context or {}).get("limit", 100)
        if value > limit:
            raise ValueError(f"value must be at most {limit}")
        return value


class NumberedPrompt(RepairPromptBuilder):
    @override
    def build(
        self,
        *,
        text: str,
        error: ParseError,
        attempt: int,
        max_attempts: int,
        instructions: str,
    ) -> Any:
        return f"attempt {attempt}/{max_attempts}: fix {text}"


@pytest.fixture
def spans() -> tuple[OpenTelemetryObserver, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return OpenTelemetryObserver(tracer_provider=provider), exporter


class TestOpenTelemetryObserver(ObserverContract):
    def make_observer(self) -> OpenTelemetryObserver:
        return OpenTelemetryObserver(tracer_provider=TracerProvider())


def test_the_wrapper_exposes_its_extension_points() -> None:
    observer = RecordingObserver()
    wrapper = with_xstructured_output(
        reply(VALID), Answer, observer=observer, name="answers"
    )

    assert isinstance(wrapper.injector, MessageInstructionInjector)
    assert isinstance(wrapper.extractor, MessageTextExtractor)
    assert wrapper.observer is observer
    assert wrapper.name == "answers"


def test_extension_points_are_type_checked() -> None:
    with pytest.raises(TypeError, match="observer must be an instance"):
        with_xstructured_output(reply(VALID), Answer, observer=object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="injector must be an instance"):
        with_xstructured_output(reply(VALID), Answer, injector=object())  # type: ignore[arg-type]


async def test_successful_calls_are_observed_without_text() -> None:
    observer = RecordingObserver()
    wrapper = with_xstructured_output(
        reply(f"Done. {VALID}"), Answer, observer=observer, name="answers"
    )

    await wrapper.ainvoke("q")

    observation = observer.only
    assert observation.operation == "invoke"
    assert observation.attributes["xstructured.name"] == "answers"
    assert observation.outcome["xstructured.envelope_count"] == 1
    assert observation.outcome["xstructured.content_chars"] == len("Done. ")
    assert not any(
        isinstance(value, str) and "Done" in value
        for value in observation.outcome.values()
    )


async def test_named_schemas_are_observed_by_name() -> None:
    observer = RecordingObserver()
    wrapper = with_xstructured_output(
        reply(
            '<xstructured>{"schema": "answer", "payload": {"value": 1}}</xstructured>'
        ),
        {"answer": Answer},
        observer=observer,
    )

    await wrapper.ainvoke("q")

    assert observer.only.outcome["xstructured.schema_name"] == "answer"


@pytest.mark.parametrize("operation", ["invoke", "stream", "transform"])
async def test_every_async_operation_is_observed(operation: str) -> None:
    observer = RecordingObserver()
    good = with_xstructured_output(reply(VALID), Answer, observer=observer)
    bad = with_xstructured_output(reply(INVALID), Answer, observer=observer)

    async def run(wrapper: Any) -> None:
        if operation == "invoke":
            await wrapper.ainvoke("q")
        elif operation == "stream":
            async for _ in wrapper.astream("q"):
                pass
        else:

            async def inputs() -> Any:
                yield "q"

            async for _ in wrapper.atransform(inputs()):
                pass

    await run(good)
    with pytest.raises(ParseError):
        await run(bad)

    success, failure = observer.observations
    assert success.operation == failure.operation == operation
    assert isinstance(success.outcome, dict)
    assert isinstance(failure.outcome, ParseError)


@pytest.mark.parametrize("operation", ["invoke", "stream", "transform"])
def test_every_sync_operation_is_observed(operation: str) -> None:
    observer = RecordingObserver()
    good = with_xstructured_output(reply(VALID), Answer, observer=observer)
    bad = with_xstructured_output(reply(INVALID), Answer, observer=observer)

    def run(wrapper: Any) -> None:
        if operation == "invoke":
            wrapper.invoke("q")
        elif operation == "stream":
            for _ in wrapper.stream("q"):
                pass
        else:
            for _ in wrapper.transform(iter(["q"])):
                pass

    run(good)
    with pytest.raises(ParseError):
        run(bad)

    success, failure = observer.observations
    assert success.operation == failure.operation == operation
    assert isinstance(success.outcome, dict)
    assert isinstance(failure.outcome, ParseError)


def test_abandoned_streams_are_observed_as_cancelled() -> None:
    observer = RecordingObserver()
    wrapper = with_xstructured_output(
        reply(f"text {VALID}"), Answer, observer=observer
    )

    events = cast("Generator[Any]", wrapper.stream("q"))
    next(events)
    events.close()

    assert isinstance(observer.only.outcome, GeneratorExit)


async def test_cancelled_calls_are_observed() -> None:
    observer = RecordingObserver()
    started = asyncio.Event()

    async def slow(_: Any) -> str:
        started.set()
        await asyncio.sleep(10)
        return VALID

    wrapper = with_xstructured_output(
        RunnableLambda(slow), Answer, observer=observer
    )
    task = asyncio.create_task(wrapper.ainvoke("q"))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert isinstance(observer.only.outcome, asyncio.CancelledError)


async def test_the_validation_context_comes_from_the_run_config() -> None:
    wrapper = with_xstructured_output(
        reply('<xstructured>{"value": 5}</xstructured>'), Limited
    )
    config: Any = {"configurable": {CONTEXT_KEY: {"limit": 3}}}

    assert (await wrapper.ainvoke("q")).structured == Limited(value=5)
    with pytest.raises(ParseError, match="at most 3"):
        await wrapper.ainvoke("q", config)
    with pytest.raises(ParseError, match="at most 3"):
        async for _ in wrapper.astream("q", config):
            pass


async def test_custom_repair_prompts_build_the_repair_input() -> None:
    repair = Recorder(VALID)
    wrapper = with_xstructured_output(
        reply(INVALID),
        Answer,
        repair=RunnableLambda(repair, afunc=repair.acall),
        repair_config=RepairConfig(max_attempts=2),
        repair_prompt=NumberedPrompt(),
    )

    result = await wrapper.ainvoke("q")

    assert result.repaired
    assert repair.inputs == [f"attempt 1/2: fix {INVALID}"]


def test_repair_prompts_require_a_repair_runnable() -> None:
    with pytest.raises(ValueError, match="require a repair Runnable"):
        with_xstructured_output(
            reply(VALID), Answer, repair_prompt=NumberedPrompt()
        )


async def test_spans_record_results_errors_and_cancellations(
    spans: tuple[OpenTelemetryObserver, InMemorySpanExporter],
) -> None:
    observer, exporter = spans
    message = AIMessage(content=VALID, id="m-1")
    good = with_xstructured_output(reply(message), Answer, observer=observer)
    bad = with_xstructured_output(reply(INVALID), Answer, observer=observer)

    await good.ainvoke("q")
    with pytest.raises(ParseError):
        await bad.ainvoke("q")
    events = cast("Generator[Any]", good.stream("q"))
    next(events)
    events.close()

    ok, failed, cancelled = exporter.get_finished_spans()
    ok_attributes = dict(ok.attributes or {})
    failed_attributes = dict(failed.attributes or {})
    cancelled_attributes = dict(cancelled.attributes or {})
    assert ok.name == "xstructured invoke"
    assert ok.status.status_code is StatusCode.OK
    assert ok_attributes["xstructured.operation"] == "invoke"
    assert ok_attributes["xstructured.envelope_count"] == 1
    assert failed.status.status_code is StatusCode.ERROR
    assert failed_attributes["error.type"] == "RecoveryError"
    assert failed.events[0].name == "exception"
    assert cancelled.name == "xstructured stream"
    assert cancelled.status.status_code is StatusCode.UNSET
    assert cancelled_attributes["xstructured.cancelled"] is True
    assert repr(observer) == "OpenTelemetryObserver()"
