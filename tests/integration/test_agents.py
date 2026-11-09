from __future__ import annotations

from typing import Any, override

import pytest
from deepagents import create_deep_agent
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, ModelResponse
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.tools import tool
from pydantic import BaseModel, Field, ValidationInfo, field_validator

from tests.support import RecordingObserver
from xstructured import (
    CONTEXT_KEY,
    LimitExceededError,
    ParseError,
    ParserConfig,
    RepairConfig,
    RepairError,
    RepairPromptBuilder,
    XStructuredResult,
)
from xstructured.agents import XStructuredMiddleware
from xstructured.testing import ScriptedChatModel


class Report(BaseModel):
    severity: str

    @field_validator("severity")
    @classmethod
    def allowed(cls, value: str, info: ValidationInfo) -> str:
        allowed = (info.context or {}).get("allowed")
        if allowed is not None and value not in allowed:
            raise ValueError(f"severity must be one of {allowed}")
        return value


VALID = 'Summary. <xstructured>{"severity": "high"}</xstructured>'
INVALID = "<xstructured>{}</xstructured>"
LOOKUP = AIMessage(
    content="",
    tool_calls=[{"name": "lookup", "args": {"key": "db"}, "id": "call-1"}],
)


class RecordingModel(ScriptedChatModel):
    """Records the messages of every call."""

    calls: list[list[BaseMessage]] = Field(default_factory=list)

    @override
    def _generate(
        self, messages: list[BaseMessage], *args: Any, **kwargs: Any
    ) -> Any:
        self.calls.append(list(messages))
        return super()._generate(messages, *args, **kwargs)


def recording(*responses: str | AIMessage) -> RecordingModel:
    return RecordingModel(messages=iter(responses), calls=[])


@tool
def lookup(key: str) -> str:
    """Look up an incident by key."""
    return f"{key} failed over"


class PromptMessages(RepairPromptBuilder):
    def __init__(self, prompt: Any) -> None:
        self.prompt = prompt
        self.attempts: list[tuple[int, int]] = []

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
        self.attempts.append((attempt, max_attempts))
        return self.prompt


def run(middleware: XStructuredMiddleware, model: Any, **kwargs: Any) -> Any:
    agent = create_agent(
        model, tools=[lookup], middleware=[middleware], **kwargs
    )
    return agent.invoke({"messages": [HumanMessage("What happened?")]})


async def arun(
    middleware: XStructuredMiddleware, model: Any, config: Any = None
) -> Any:
    agent = create_agent(model, tools=[lookup], middleware=[middleware])
    return await agent.ainvoke(
        {"messages": [HumanMessage("What happened?")]}, config
    )


def test_final_answers_become_the_structured_response() -> None:
    model = recording(VALID)
    middleware = XStructuredMiddleware(Report)

    state = run(middleware, model)

    result = state["structured_response"]
    assert isinstance(result, XStructuredResult)
    assert result.structured == Report(severity="high")
    assert result.content == "Summary. "
    assert state["messages"][-1].content == VALID
    system = model.calls[0][0]
    assert isinstance(system, SystemMessage)
    assert system.content == middleware.instructions


async def test_tool_calls_pass_through_to_the_tools() -> None:
    model = recording(LOOKUP, VALID)

    state = await arun(XStructuredMiddleware(Report), model)

    assert state["structured_response"].structured.severity == "high"
    assert [m.type for m in state["messages"]] == ["human", "ai", "tool", "ai"]
    assert all(
        call[0].text.endswith(XStructuredMiddleware(Report).instructions)
        for call in model.calls
    )


def test_existing_system_prompts_are_extended() -> None:
    model = recording(VALID)

    run(XStructuredMiddleware(Report), model, system_prompt="Be brief.")

    content = model.calls[0][0].text
    assert content.startswith("Be brief.\n\n")
    assert content.endswith(XStructuredMiddleware(Report).instructions)


def test_instructions_can_live_in_the_agent_prompt() -> None:
    model = recording(VALID)
    middleware = XStructuredMiddleware(Report, inject_instructions=False)

    state = run(middleware, model, system_prompt=middleware.instructions)

    assert state["structured_response"].structured.severity == "high"
    assert model.calls[0][0].text == middleware.instructions


def test_invalid_answers_fail_without_repair() -> None:
    with pytest.raises(ParseError):
        run(XStructuredMiddleware(Report), recording(INVALID))


@pytest.mark.parametrize("is_async", [False, True])
async def test_invalid_answers_are_repaired(is_async: bool) -> None:
    model = recording(INVALID, VALID)
    middleware = XStructuredMiddleware(
        Report, repair_config=RepairConfig(max_attempts=2)
    )

    state = (
        await arun(middleware, model) if is_async else run(middleware, model)
    )

    result = state["structured_response"]
    assert result.repaired
    assert result.repair_attempts == 1
    assert [m.type for m in state["messages"]] == ["human", "ai"]
    assert state["messages"][-1].content == VALID
    repair_call = model.calls[1]
    assert repair_call[-2].content == INVALID
    assert isinstance(repair_call[-1], HumanMessage)
    assert "Problems (attempt 1 of 2)" in repair_call[-1].content


@pytest.mark.parametrize("is_async", [False, True])
async def test_repair_stops_when_the_budget_is_spent(is_async: bool) -> None:
    model = recording(INVALID, INVALID, LOOKUP)
    middleware = XStructuredMiddleware(
        Report, repair_config=RepairConfig(max_attempts=2)
    )

    async def attempt() -> Any:
        return (
            await arun(middleware, model)
            if is_async
            else run(middleware, model)
        )

    with pytest.raises(RepairError) as caught:
        await attempt()

    assert caught.value.attempts == 2
    assert len(model.calls) == 3


def test_tool_calls_during_repair_count_as_failures() -> None:
    model = recording(INVALID, LOOKUP)
    middleware = XStructuredMiddleware(
        Report, repair_config=RepairConfig(max_attempts=1)
    )

    with pytest.raises(RepairError) as caught:
        run(middleware, model)

    assert "called tools instead of answering" in caught.value.failures[0]


def test_limit_errors_are_not_repaired() -> None:
    middleware = XStructuredMiddleware(
        Report,
        parser_config=ParserConfig(max_input_chars=10),
        repair_config=RepairConfig(),
    )

    with pytest.raises(LimitExceededError):
        run(middleware, recording(VALID))


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        (SystemMessage("Fix it."), ["system"]),
        ([HumanMessage("Fix"), HumanMessage("it")], ["human", "human"]),
    ],
)
def test_custom_repair_prompts_are_appended(
    prompt: Any, expected: list[str]
) -> None:
    model = recording(INVALID, VALID)
    builder = PromptMessages(prompt)
    middleware = XStructuredMiddleware(
        Report,
        repair_config=RepairConfig(max_attempts=3),
        repair_prompt=builder,
    )

    run(middleware, model)

    assert builder.attempts == [(1, 3)]
    assert [m.type for m in model.calls[1][-len(expected) :]] == expected


def test_unsupported_repair_prompts_fail() -> None:
    middleware = XStructuredMiddleware(
        Report,
        repair_config=RepairConfig(),
        repair_prompt=PromptMessages(42),
    )

    with pytest.raises(TypeError, match="repair_prompt must build"):
        run(middleware, recording(INVALID, VALID))


def test_repair_prompts_require_repair_config() -> None:
    with pytest.raises(ValueError, match="requires repair_config"):
        XStructuredMiddleware(Report, repair_prompt=PromptMessages("x"))


def test_extension_points_are_type_checked() -> None:
    with pytest.raises(TypeError, match="observer must be an instance"):
        XStructuredMiddleware(Report, observer=object())  # type: ignore[arg-type]


async def test_the_validation_context_comes_from_the_agent_config() -> None:
    config = {"configurable": {CONTEXT_KEY: {"allowed": ["low"]}}}

    with pytest.raises(ParseError, match="must be one of"):
        await arun(XStructuredMiddleware(Report), recording(VALID), config)


async def test_final_answers_are_observed() -> None:
    observer = RecordingObserver()
    middleware = XStructuredMiddleware(Report, observer=observer, name="report")

    await arun(middleware, recording(LOOKUP, VALID))
    with pytest.raises(ParseError):
        await arun(middleware, recording(INVALID))

    success, failure = observer.observations
    assert success.operation == failure.operation == "agent"
    assert success.attributes["xstructured.name"] == "report"
    assert success.outcome["xstructured.envelope_count"] == 1
    assert isinstance(failure.outcome, ParseError)


def test_the_middleware_describes_itself() -> None:
    middleware = XStructuredMiddleware(Report, name="report")

    assert middleware.name == "report"
    assert XStructuredMiddleware(Report).name == "XStructuredMiddleware"
    assert repr(middleware) == "XStructuredMiddleware(name='report')"
    assert middleware.parser.config.require_envelope
    required = ParserConfig(require_envelope=True)
    assert (
        XStructuredMiddleware(Report, parser_config=required).parser.config
        is required
    )
    assert len(middleware.schema_fingerprint) == 64


@pytest.mark.parametrize("is_async", [False, True])
async def test_responses_without_messages_pass_through(is_async: bool) -> None:
    middleware = XStructuredMiddleware(Report)
    request = ModelRequest(model=ScriptedChatModel.of(), messages=[])
    empty = ModelResponse(result=[HumanMessage("not an answer")])

    async def ahandler(_: ModelRequest[Any]) -> ModelResponse[Any]:
        return empty

    response = (
        await middleware.awrap_model_call(request, ahandler)
        if is_async
        else middleware.wrap_model_call(request, lambda _: empty)
    )

    assert response is empty


async def test_deep_agents_get_a_structured_response() -> None:
    agent = create_deep_agent(
        model=ScriptedChatModel.of(VALID),
        middleware=[XStructuredMiddleware(Report)],
    )

    state = await agent.ainvoke({"messages": [HumanMessage("What happened?")]})

    assert state["structured_response"].structured.severity == "high"
