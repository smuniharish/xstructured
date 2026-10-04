from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda

from tests.support import Answer, ChunkRunnable, Label, Recorder, reply
from xstructured import (
    EnvelopeSpec,
    LimitExceededError,
    ParseError,
    ParserConfig,
    RepairConfig,
    XStructuredResult,
    XStructuredRunnable,
    fingerprint_schema,
    with_xstructured_output,
)

ENVELOPED = 'The answer is 42. <xstructured>{"value": 42}</xstructured> Done.'


def test_invoke_returns_text_value_and_provenance() -> None:
    message = AIMessage(
        content=ENVELOPED,
        id="msg-1",
        response_metadata={"model_name": "fake"},
        usage_metadata={
            "input_tokens": 5,
            "output_tokens": 7,
            "total_tokens": 12,
        },
    )
    wrapper = with_xstructured_output(reply(message), Answer)

    result = wrapper.invoke("What is six times seven?")

    assert isinstance(result, XStructuredResult)
    assert result.structured == Answer(value=42)
    assert result.content == "The answer is 42.  Done."
    assert result.raw is message
    assert result.raw_text == ENVELOPED
    assert result.json_text == '{"value": 42}'
    assert not result.recovered
    assert not result.repaired
    assert result.repair_attempts == 0
    assert result.schema_name is None
    assert result.metadata["schema_fingerprint"] == fingerprint_schema(Answer)
    assert result.metadata["envelope_count"] == 1
    assert result.metadata["parse_duration"] >= 0
    assert result.metadata["message_id"] == "msg-1"
    assert result.metadata["response_metadata"] == {"model_name": "fake"}
    assert result.metadata["usage_metadata"]["total_tokens"] == 12
    with pytest.raises(TypeError):
        result.metadata["extra"] = 1  # type: ignore[index]


def test_string_outputs_have_no_message_metadata() -> None:
    result = with_xstructured_output(reply(ENVELOPED), Answer).invoke("q")

    assert set(result.metadata) == {
        "schema_fingerprint",
        "envelope_count",
        "parse_duration",
    }


def test_instructions_are_added_to_string_and_message_inputs() -> None:
    recorder = Recorder(ENVELOPED)
    wrapper = with_xstructured_output(RunnableLambda(recorder), Answer)

    wrapper.invoke("question")
    wrapper.invoke([HumanMessage("question")])
    wrapper.invoke([("system", "Be brief."), ("human", "question")])

    assert recorder.inputs[0] == f"question\n\n{wrapper.instructions}"
    assert [m.type for m in recorder.inputs[1]] == ["system", "human"]
    assert (
        recorder.inputs[2][0].content == f"Be brief.\n\n{wrapper.instructions}"
    )


def test_unsupported_inputs_fail_before_calling_the_model() -> None:
    recorder = Recorder(ENVELOPED)
    wrapper = with_xstructured_output(RunnableLambda(recorder), Answer)

    with pytest.raises(TypeError, match="inject_instructions=False"):
        wrapper.invoke({"messages": [HumanMessage("hi")]})
    assert recorder.inputs == []


def test_instruction_injection_can_be_disabled() -> None:
    recorder = Recorder(ENVELOPED)
    wrapper = with_xstructured_output(
        RunnableLambda(recorder), Answer, inject_instructions=False
    )

    assert wrapper.invoke({"question": "hi"}).structured == Answer(value=42)
    assert recorder.inputs == [{"question": "hi"}]


async def test_ainvoke_matches_invoke() -> None:
    async def respond(_: Any) -> str:
        return ENVELOPED

    wrapper = with_xstructured_output(RunnableLambda(respond), Answer)

    result = await wrapper.ainvoke("q")

    assert result.structured == Answer(value=42)
    assert result.content == "The answer is 42.  Done."


def test_batch_and_abatch_use_native_runnable_semantics() -> None:
    wrapper = with_xstructured_output(
        RunnableLambda(
            lambda text: f'<xstructured>{{"value": {len(text)}}}</xstructured>'
        ),
        Answer,
        inject_instructions=False,
    )

    assert [r.structured.value for r in wrapper.batch(["a", "bb"])] == [1, 2]
    errors = wrapper.batch(["a", 3], return_exceptions=True)
    assert isinstance(errors[1], TypeError)


async def test_abatch() -> None:
    wrapper = with_xstructured_output(reply(ENVELOPED), Answer)

    results = await wrapper.abatch(["a", "b"], config={"max_concurrency": 2})

    assert [r.structured for r in results] == [
        Answer(value=42),
        Answer(value=42),
    ]


def test_responses_without_an_envelope_are_rejected() -> None:
    wrapper = with_xstructured_output(reply('{"value": 1}'), Answer)

    with pytest.raises(ParseError, match="No complete <xstructured>"):
        wrapper.invoke("q")


def test_custom_envelopes_and_parser_limits() -> None:
    wrapper = with_xstructured_output(
        reply("[[" + '{"value": 1}' + "]]"),
        Answer,
        envelope=EnvelopeSpec("[[", "]]"),
        parser_config=ParserConfig(max_input_chars=100),
    )

    assert wrapper.invoke("q").structured == Answer(value=1)
    assert "[[JSON]]" in wrapper.instructions
    assert wrapper.parser.config.require_envelope
    assert wrapper.parser.config.max_input_chars == 100
    with pytest.raises(LimitExceededError):
        with_xstructured_output(
            reply("x" * 200),
            Answer,
            parser_config=ParserConfig(max_input_chars=100),
        ).invoke("q")


def test_multiple_values_and_named_schemas() -> None:
    wrapper = with_xstructured_output(
        reply(
            "<xstructured>["
            '{"schema": "answer", "payload": {"value": 1}},'
            '{"schema": "label", "payload": {"name": "ready"}}'
            "]</xstructured>"
        ),
        {"answer": Answer, "label": Label},
        multiple=True,
    )

    result = wrapper.invoke("q")

    assert result.structured == [Answer(value=1), Label(name="ready")]
    assert result.schema_name is None
    assert '"schema": "<name>"' in wrapper.instructions


def test_named_envelopes_return_a_dict_and_count_envelopes() -> None:
    wrapper = with_xstructured_output(
        reply(
            'Finding: <xstructured name="answer">{"value": 1}</xstructured>\n'
            'Action: <xstructured name="label">{"name": "ship"}</xstructured>'
        ),
        {"answer": Answer, "label": Label},
        multiple_envelopes=True,
    )

    result = wrapper.invoke("q")

    assert result.structured == {
        "answer": Answer(value=1),
        "label": Label(name="ship"),
    }
    assert result.content == "Finding: \nAction: "
    assert result.metadata["envelope_count"] == 2


def test_wrapper_properties_and_runnable_schema() -> None:
    def typed(question: str) -> str:
        return ENVELOPED

    inner = RunnableLambda(typed)
    wrapper = with_xstructured_output(inner, Answer)

    assert isinstance(wrapper, XStructuredRunnable)
    assert wrapper.runnable is inner
    assert wrapper.envelope == EnvelopeSpec()
    assert wrapper.schema_fingerprint == fingerprint_schema(Answer)
    assert wrapper.InputType == inner.InputType
    assert wrapper.OutputType is XStructuredResult
    assert wrapper.get_input_jsonschema() == {
        "title": "XStructuredRunnableInput",
        "type": "string",
    }
    assert (
        wrapper.get_output_jsonschema()["$ref"] == "#/$defs/XStructuredResult"
    )
    assert repr(wrapper) == f"XStructuredRunnable({inner!r})"


def test_an_explicitly_required_envelope_is_kept() -> None:
    config = ParserConfig(require_envelope=True, max_payload_chars=50)
    wrapper = with_xstructured_output(
        reply(ENVELOPED), Answer, parser_config=config
    )

    assert wrapper.parser.config is config
    assert wrapper.invoke("q").structured == Answer(value=42)


def test_repair_config_requires_a_repair_runnable() -> None:
    with pytest.raises(ValueError, match="repair_config requires"):
        with_xstructured_output(
            reply(ENVELOPED), Answer, repair_config=RepairConfig()
        )


def test_unsupported_outputs_are_reported() -> None:
    with pytest.raises(TypeError, match="must return str or BaseMessage"):
        with_xstructured_output(reply({"messages": []}), Answer).invoke("q")


def test_message_chunks_from_invoke_are_supported() -> None:
    wrapper = with_xstructured_output(ChunkRunnable([ENVELOPED]), Answer)

    assert wrapper.invoke("q").structured == Answer(value=42)
