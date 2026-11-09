from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, Generation
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ValidationInfo, field_validator

from tests.support import Answer
from xstructured import (
    CONTEXT_KEY,
    EnvelopeSpec,
    ParseError,
    ParserConfig,
    XStructuredOutputParser,
    XStructuredResult,
    fingerprint_schema,
    schema_instructions,
)
from xstructured.testing import ScriptedChatModel

VALID = 'Done. <xstructured>{"value": 1}</xstructured>'


def test_format_instructions_and_metadata() -> None:
    parser = XStructuredOutputParser(Answer)

    assert parser.get_format_instructions() == schema_instructions(
        Answer, envelope=EnvelopeSpec()
    )
    assert parser.schema_fingerprint == fingerprint_schema(parser.parser.schema)
    assert parser.OutputType is XStructuredResult
    assert parser._type == "xstructured"


def test_an_envelope_is_always_required() -> None:
    parser = XStructuredOutputParser(
        Answer, parser_config=ParserConfig(require_envelope=False)
    )

    assert parser.parser.config.require_envelope
    required = ParserConfig(require_envelope=True)
    assert (
        XStructuredOutputParser(Answer, parser_config=required).parser.config
        is required
    )
    with pytest.raises(ParseError):
        parser.parse('{"value": 1}')


def test_text_is_parsed() -> None:
    result = XStructuredOutputParser(Answer).parse(VALID)

    assert result.structured == Answer(value=1)
    assert result.content == "Done. "
    assert result.raw == VALID


def test_chat_generations_keep_their_message() -> None:
    message = AIMessage(content=VALID, id="m-1")

    result = XStructuredOutputParser(Answer).parse_result(
        [ChatGeneration(message=message)]
    )

    assert result.raw is message
    assert result.metadata["message_id"] == "m-1"


def test_text_generations_keep_their_text() -> None:
    result = XStructuredOutputParser(Answer).parse_result(
        [Generation(text=VALID)]
    )

    assert result.raw == VALID


async def test_async_parsing_matches_sync_parsing() -> None:
    parser = XStructuredOutputParser(Answer)

    text = await parser.aparse(VALID)
    generation = await parser.aparse_result([Generation(text=VALID)])

    assert text.structured == generation.structured == Answer(value=1)


class Limited(BaseModel):
    value: int

    @field_validator("value")
    @classmethod
    def within_limit(cls, value: int, info: ValidationInfo) -> int:
        if value > (info.context or {}).get("limit", 100):
            raise ValueError("value is over the limit")
        return value


async def test_chains_pass_the_validation_context() -> None:
    def chain() -> Any:
        return (
            ChatPromptTemplate.from_messages([("human", "{q}")])
            | ScriptedChatModel.of(VALID.replace("1", "5"))
            | XStructuredOutputParser(Limited)
        )

    limited: Any = {"configurable": {CONTEXT_KEY: {"limit": 3}}}

    assert (await chain().ainvoke({"q": "x"})).structured == Limited(value=5)
    with pytest.raises(ParseError, match="over the limit"):
        await chain().ainvoke({"q": "x"}, limited)
