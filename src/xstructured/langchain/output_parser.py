"""LangChain output parser for prompt | model | parser chains."""

from __future__ import annotations

from time import perf_counter
from typing import Any, override

from langchain_core.output_parsers import BaseOutputParser
from langchain_core.outputs import ChatGeneration, Generation
from langchain_core.runnables.config import ensure_config
from pydantic import PrivateAttr

from xstructured.contracts import (
    InstructionRenderer,
    JsonDecoder,
    RecoveryStrategy,
)
from xstructured.core.config import ParserConfig
from xstructured.core.result import XStructuredResult
from xstructured.envelope.spec import EnvelopeSpec
from xstructured.parser.parser import StructuredParser
from xstructured.schema.fingerprint import fingerprint_schema
from xstructured.schema.instructions import schema_instructions
from xstructured.schema.introspection import SchemaInfo, SchemaTarget
from xstructured.schema.named import NamedSchemas, NamedSchemaTargets
from xstructured.schema.options import SchemaOptions

from ._shared import build_result, remove_spans, validation_context

__all__ = ["XStructuredOutputParser"]


class XStructuredOutputParser(BaseOutputParser[XStructuredResult[Any]]):
    """Parse model output into an `XStructuredResult` inside a LangChain chain.

    Use it when the prompt is built separately, for example with a
    `ChatPromptTemplate` that includes `get_format_instructions()`. The
    validation context is read from ``config["configurable"]["xstructured_context"]``.
    Parsing is CPU-bound, so `ainvoke` parses on the event loop without a thread.

    Args:
        schema: A schema target, a `SchemaInfo`, or named schemas.
        envelope: Envelope delimiters. Defaults to ``<xstructured>`` / ``</xstructured>``.
        parser_config: Limits and recovery settings. An envelope is always required.
        multiple: Expect a JSON array of values.
        multiple_envelopes: Expect one named envelope per applicable named schema.
        schema_options: Pydantic configuration and JSON Schema generation options.
        renderer: An `InstructionRenderer` for the format instructions.
        recovery: A `RecoveryStrategy` choosing the substrings tried as JSON.
        decoder: A `JsonDecoder` for each candidate.

    Example:
        ```python
        import asyncio

        from langchain_core.prompts import ChatPromptTemplate
        from pydantic import BaseModel
        from xstructured import XStructuredOutputParser
        from xstructured.testing import ScriptedChatModel


        class Contact(BaseModel):
            name: str
            email: str


        parser = XStructuredOutputParser(Contact)
        prompt = ChatPromptTemplate.from_messages(
            [("system", "{format_instructions}"), ("human", "{text}")]
        ).partial(format_instructions=parser.get_format_instructions())
        model = ScriptedChatModel.of(
            'Found one. <xstructured>{"name": "Priya", '
            '"email": "priya@example.com"}</xstructured>'
        )


        async def main() -> None:
            chain = prompt | model | parser
            result = await chain.ainvoke(
                {"text": "Reach Priya at priya@example.com."}
            )
            assert result.structured == Contact(
                name="Priya", email="priya@example.com"
            )
            assert result.content == "Found one. "


        asyncio.run(main())
        ```
    """

    _parser: StructuredParser[Any] = PrivateAttr()
    _instructions: str = PrivateAttr()
    _fingerprint: str = PrivateAttr()

    def __init__(
        self,
        schema: SchemaTarget | SchemaInfo | NamedSchemaTargets | NamedSchemas,
        *,
        envelope: EnvelopeSpec | None = None,
        parser_config: ParserConfig | None = None,
        multiple: bool = False,
        multiple_envelopes: bool = False,
        schema_options: SchemaOptions | None = None,
        renderer: InstructionRenderer | None = None,
        recovery: RecoveryStrategy | None = None,
        decoder: JsonDecoder | None = None,
    ) -> None:
        super().__init__()
        envelope = envelope or EnvelopeSpec()
        config = parser_config or ParserConfig()
        if not config.require_envelope:
            config = config.model_copy(update={"require_envelope": True})
        self._parser = StructuredParser(
            schema,
            config=config,
            envelope=envelope,
            multiple=multiple,
            multiple_envelopes=multiple_envelopes,
            schema_options=schema_options,
            recovery=recovery,
            decoder=decoder,
        )
        self._instructions = schema_instructions(
            self._parser.schema,
            envelope=envelope,
            multiple=multiple,
            multiple_envelopes=multiple_envelopes,
            renderer=renderer,
        )
        self._fingerprint = fingerprint_schema(self._parser.schema)

    @property
    def parser(self) -> StructuredParser[Any]:
        """The parser used for every response."""
        return self._parser

    @property
    def schema_fingerprint(self) -> str:
        """SHA-256 fingerprint of the schema (see `fingerprint_schema`)."""
        return self._fingerprint

    @property
    @override
    def OutputType(self) -> type[XStructuredResult[Any]]:
        """`XStructuredResult`."""
        return XStructuredResult

    @property
    @override
    def _type(self) -> str:
        return "xstructured"

    @override
    def get_format_instructions(self) -> str:
        """Return the instructions to place in the prompt."""
        return self._instructions

    @override
    def parse(self, text: str) -> XStructuredResult[Any]:
        """Parse *text*.

        Raises:
            ParseError: If the text does not validate.
        """
        return self._parse(text, text)

    @override
    def parse_result(
        self, result: list[Generation], *, partial: bool = False
    ) -> XStructuredResult[Any]:
        """Parse the first generation, keeping its message as `XStructuredResult.raw`.

        Raises:
            ParseError: If the text does not validate.
        """
        del partial
        generation = result[0]
        raw = (
            generation.message
            if isinstance(generation, ChatGeneration)
            else generation.text
        )
        return self._parse(generation.text, raw)

    @override
    async def aparse_result(
        self, result: list[Generation], *, partial: bool = False
    ) -> XStructuredResult[Any]:
        return self.parse_result(result, partial=partial)

    @override
    async def aparse(self, text: str) -> XStructuredResult[Any]:
        return self.parse(text)

    def _parse(self, text: str, raw: Any) -> XStructuredResult[Any]:
        started = perf_counter()
        parsed = self._parser.parse(
            text, context=validation_context(ensure_config())
        )
        return build_result(
            fingerprint=self._fingerprint,
            raw=raw,
            raw_text=text,
            content=remove_spans(text, parsed.envelope_spans),
            parsed=parsed,
            envelope_count=len(parsed.envelope_spans),
            parse_duration=perf_counter() - started,
        )
