from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.prompt_values import ChatPromptValue, StringPromptValue

from xstructured import (
    INSTRUCTIONS_MESSAGE_ID,
    InstructionInjector,
    MessageInstructionInjector,
    MessageTextExtractor,
    OutputTextExtractor,
)
from xstructured.langchain._messages import ChunkAccumulator
from xstructured.testing import (
    InstructionInjectorContract,
    OutputTextExtractorContract,
)

RULES = "Use the envelope."
inject = MessageInstructionInjector().inject
extractor = MessageTextExtractor()


class TestStringInjector(InstructionInjectorContract):
    def make_injector(self) -> InstructionInjector:
        return MessageInstructionInjector()

    def make_input(self) -> Any:
        return "Question?"


class TestStateInjector(InstructionInjectorContract):
    def make_injector(self) -> InstructionInjector:
        return MessageInstructionInjector()

    def make_input(self) -> Any:
        return {"messages": [HumanMessage("hi")], "topic": "x"}


class TestMessageExtractor(OutputTextExtractorContract):
    def make_extractor(self) -> OutputTextExtractor:
        return MessageTextExtractor()

    def make_output(self, text: str) -> Any:
        return AIMessage(content=text)

    def make_chunks(self, text: str) -> list[Any]:
        middle = len(text) // 2
        return [
            (
                AIMessageChunk(content=text[:middle]),
                {"langgraph_node": "model"},
            ),
            (ToolMessage(content="ignored", tool_call_id="1"), {}),
            (
                AIMessageChunk(content=text[middle:]),
                {"langgraph_node": "model"},
            ),
        ]


class TestStateExtractor(OutputTextExtractorContract):
    def make_extractor(self) -> OutputTextExtractor:
        return MessageTextExtractor()

    def make_output(self, text: str) -> Any:
        return {
            "messages": [
                HumanMessage("q"),
                AIMessage(text),
                ToolMessage("t", tool_call_id="1"),
            ]
        }


def test_text_accepts_strings_messages_and_state() -> None:
    assert extractor.text("plain") == "plain"
    assert (
        extractor.text(AIMessage(content=[{"type": "text", "text": "blocks"}]))
        == "blocks"
    )
    with pytest.raises(TypeError, match="must return str, BaseMessage"):
        extractor.text({"question": "x"})
    with pytest.raises(TypeError, match="contain no AI message"):
        extractor.text({"messages": [HumanMessage("q")]})


def test_chunk_text_filters_by_node_and_message_type() -> None:
    only_agent = MessageTextExtractor(nodes=["agent"])
    chunk = AIMessageChunk(content="x")

    assert only_agent.chunk_text((chunk, {"langgraph_node": "agent"})) == "x"
    assert only_agent.chunk_text((chunk, {"langgraph_node": "tools"})) == ""
    assert only_agent.chunk_text((chunk, "not metadata")) == ""
    assert extractor.chunk_text((HumanMessage("q"), {})) == ""
    assert extractor.chunk_text("plain") == "plain"
    assert repr(only_agent) == (
        "MessageTextExtractor(messages_key='messages', nodes=['agent'])"
    )
    assert repr(extractor) == (
        "MessageTextExtractor(messages_key='messages', nodes=None)"
    )


def test_string_chunks_are_joined() -> None:
    chunks = ChunkAccumulator(extractor)

    assert chunks.add("a") == "a"
    chunks.add("b")

    assert chunks.text == "ab"
    assert chunks.output() == "ab"
    assert ChunkAccumulator(extractor).output() == ""


def test_message_chunks_are_merged_into_one_message() -> None:
    chunks = ChunkAccumulator(extractor)
    chunks.add(AIMessageChunk(content="Hel", id="run-1"))
    chunks.add(
        AIMessageChunk(
            content="lo",
            usage_metadata={
                "input_tokens": 3,
                "output_tokens": 2,
                "total_tokens": 5,
            },
        )
    )

    merged = chunks.output()

    assert isinstance(merged, AIMessage)
    assert merged.text == "Hello"
    assert merged.id == "run-1"
    assert merged.usage_metadata == {
        "input_tokens": 3,
        "output_tokens": 2,
        "total_tokens": 5,
    }


def test_graph_message_tuples_keep_only_response_messages() -> None:
    chunks = ChunkAccumulator(extractor)
    chunks.add((AIMessageChunk(content="Hel", id="run-1"), {}))
    assert chunks.add((ToolMessage(content="tool", tool_call_id="1"), {})) == ""
    chunks.add((AIMessageChunk(content="lo"), {}))

    merged = chunks.output()

    assert chunks.text == "Hello"
    assert isinstance(merged, AIMessage)
    assert merged.text == "Hello"


def test_unmergeable_chunks_are_kept_as_they_are() -> None:
    message = AIMessage(content="whole")
    single = ChunkAccumulator(extractor)
    single.add(message)
    mixed = ChunkAccumulator(extractor)
    mixed.add("a")
    mixed.add(message)

    assert single.output() is message
    assert mixed.output() == ("a", message)


def test_strings_get_instructions_appended() -> None:
    assert inject("Question?", RULES) == f"Question?\n\n{RULES}"


def test_messages_get_a_leading_system_message() -> None:
    messages = inject([HumanMessage("hi")], RULES)

    assert [m.type for m in messages] == ["system", "human"]
    assert messages[0].content == RULES
    assert messages[0].id is None


def test_message_like_inputs_are_normalized() -> None:
    messages = inject(
        [("human", "hi"), {"role": "user", "content": "x"}], RULES
    )

    assert [m.type for m in messages] == ["system", "human", "human"]


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("Be brief.", f"Be brief.\n\n{RULES}"),
        ("", RULES),
        (
            [{"type": "text", "text": "Be brief."}],
            [
                {"type": "text", "text": "Be brief."},
                {"type": "text", "text": RULES},
            ],
        ),
    ],
)
def test_existing_system_messages_are_extended(
    content: object, expected: object
) -> None:
    system = SystemMessage(content=content, id="sys-1")  # type: ignore[arg-type]

    messages = inject([system, HumanMessage("hi")], RULES)

    assert len(messages) == 2
    assert messages[0].content == expected
    assert messages[0].id == "sys-1"
    assert system.content == content


@pytest.mark.parametrize(
    "content", [f"Be brief.\n\n{RULES}", [{"type": "text", "text": RULES}]]
)
def test_instructions_are_added_once(content: object) -> None:
    messages = [SystemMessage(content=content), HumanMessage("hi")]  # type: ignore[arg-type]

    assert inject(messages, RULES) == messages


def test_prompt_values_become_chat_prompt_values() -> None:
    value = inject(StringPromptValue(text="hi"), RULES)

    assert isinstance(value, ChatPromptValue)
    assert [m.type for m in value.to_messages()] == ["system", "human"]


def test_state_mappings_get_an_identified_system_message() -> None:
    state = {"messages": [("human", "hi")], "topic": "x"}

    injected = inject(state, RULES)

    assert injected["topic"] == "x"
    assert [m.type for m in injected["messages"]] == ["system", "human"]
    assert injected["messages"][0].id == INSTRUCTIONS_MESSAGE_ID
    assert state == {"messages": [("human", "hi")], "topic": "x"}


def test_the_messages_key_is_configurable() -> None:
    injector = MessageInstructionInjector(messages_key="history")

    injected = injector.inject({"history": [HumanMessage("hi")]}, RULES)

    assert [m.type for m in injected["history"]] == ["system", "human"]
    assert (
        repr(injector) == "MessageInstructionInjector(messages_key='history')"
    )
    with pytest.raises(TypeError, match="'history' key"):
        injector.inject({"messages": []}, RULES)


@pytest.mark.parametrize(
    "value",
    [
        {"question": "hi"},
        {"messages": "not a list"},
        42,
        b"bytes",
        [("unknown-role", "x")],
        [object()],
    ],
)
def test_inputs_that_cannot_carry_instructions_fail_fast(value: object) -> None:
    with pytest.raises(TypeError, match="inject_instructions=False"):
        inject(value, RULES)
