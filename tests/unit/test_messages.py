from __future__ import annotations

import pytest
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    SystemMessage,
)
from langchain_core.prompt_values import ChatPromptValue, StringPromptValue

from xstructured.langchain._messages import (
    ChunkAccumulator,
    inject_instructions,
    output_text,
)

RULES = "Use the envelope."


def test_output_text_accepts_strings_and_messages() -> None:
    assert output_text("plain") == "plain"
    assert (
        output_text(AIMessage(content=[{"type": "text", "text": "blocks"}]))
        == "blocks"
    )
    with pytest.raises(TypeError, match="must return str or BaseMessage"):
        output_text({"messages": []})


def test_string_chunks_are_joined() -> None:
    chunks = ChunkAccumulator()

    assert chunks.add("a") == "a"
    chunks.add("b")

    assert chunks.text == "ab"
    assert chunks.output() == "ab"
    assert ChunkAccumulator().output() == ""


def test_message_chunks_are_merged_into_one_message() -> None:
    chunks = ChunkAccumulator()
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


def test_unmergeable_chunks_are_kept_as_they_are() -> None:
    message = AIMessage(content="whole")
    single = ChunkAccumulator()
    single.add(message)
    mixed = ChunkAccumulator()
    mixed.add("a")
    mixed.add(message)

    assert single.output() is message
    assert mixed.output() == ("a", message)


def test_strings_get_instructions_appended() -> None:
    assert inject_instructions("Question?", RULES) == f"Question?\n\n{RULES}"


def test_messages_get_a_leading_system_message() -> None:
    messages = inject_instructions([HumanMessage("hi")], RULES)

    assert [m.type for m in messages] == ["system", "human"]
    assert messages[0].content == RULES


def test_message_like_inputs_are_normalized() -> None:
    messages = inject_instructions(
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

    messages = inject_instructions([system, HumanMessage("hi")], RULES)

    assert len(messages) == 2
    assert messages[0].content == expected
    assert messages[0].id == "sys-1"
    assert system.content == content


def test_prompt_values_become_chat_prompt_values() -> None:
    value = inject_instructions(StringPromptValue(text="hi"), RULES)

    assert isinstance(value, ChatPromptValue)
    assert [m.type for m in value.to_messages()] == ["system", "human"]


@pytest.mark.parametrize(
    "value",
    [
        {"messages": []},
        {"question": "hi"},
        42,
        b"bytes",
        [("unknown-role", "x")],
        [object()],
    ],
)
def test_inputs_that_cannot_carry_instructions_fail_fast(value: object) -> None:
    with pytest.raises(TypeError, match="inject_instructions=False"):
        inject_instructions(value, RULES)
