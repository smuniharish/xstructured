"""LangChain Runnable integration for the xstructured protocol."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator, Iterator, Mapping, Sequence
from time import perf_counter
from types import MappingProxyType
from typing import Any, Generic, Literal, TypeVar, cast, overload

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import Runnable, RunnableConfig

from xstructured.core import ParseError, ParserConfig, RepairConfig
from xstructured.envelope import EnvelopeSpec
from xstructured.parser import StructuredParser
from xstructured.schema import (
    NamedSchemas,
    NamedSchemaTargets,
    SchemaTarget,
    fingerprint_schema,
    inspect_named_schemas,
    schema_instructions,
)
from xstructured.streaming import StreamDecoder, StreamEvent, StreamEventKind

from ._support import output_text
from .repair import Repairer
from .result import XStructuredResult

Input = TypeVar("Input")
T = TypeVar("T")


class XStructuredRunnable(
    Runnable[Input, XStructuredResult[T] | StreamEvent[T]],
    Generic[Input, T],
):
    """A Runnable that applies and decodes the xstructured protocol."""

    def __init__(
        self,
        runnable: Runnable[Input, Any],
        schema: SchemaTarget | NamedSchemaTargets | NamedSchemas,
        *,
        envelope: EnvelopeSpec | None = None,
        parser_config: ParserConfig | None = None,
        multiple: bool = False,
        multiple_envelopes: bool = False,
        inject_instructions: bool = True,
        repair: Runnable[Any, Any] | None = None,
        repair_config: RepairConfig | None = None,
    ) -> None:
        self._runnable = runnable
        self.envelope = envelope or EnvelopeSpec()
        config = parser_config or ParserConfig()
        if not config.require_envelope:
            config = config.model_copy(update={"require_envelope": True})
        self._parser: StructuredParser[T] = StructuredParser(
            schema,
            config=config,
            envelope=self.envelope,
            multiple=multiple,
            multiple_envelopes=multiple_envelopes,
        )
        instruction_schema = (
            inspect_named_schemas(schema) if isinstance(schema, Mapping) else schema
        )
        self.instructions = schema_instructions(
            instruction_schema,
            envelope=self.envelope.start,
            multiple=multiple,
            multiple_envelopes=multiple_envelopes,
        )
        self.schema_fingerprint = fingerprint_schema(schema)
        self.inject_instructions = inject_instructions
        self.multiple = multiple
        self.multiple_envelopes = multiple_envelopes
        self._repairer: Repairer[T] | None = (
            Repairer(self._parser, repair, repair_config or RepairConfig(), self.instructions)
            if repair is not None
            else None
        )

    def invoke(
        self,
        input: Input,  # noqa: A002 - LangChain Runnable API compatibility
        config: RunnableConfig | None = None,
        **kwargs: Any | None,
    ) -> XStructuredResult[T]:
        """Invoke the wrapped Runnable and parse its complete response."""
        raw = self._runnable.invoke(
            self._prepare_input(input),
            config=config,
            **kwargs,
        )
        return self._parse_output(raw, config=config)

    async def ainvoke(
        self,
        input: Input,  # noqa: A002 - LangChain Runnable API compatibility
        config: RunnableConfig | None = None,
        **kwargs: Any | None,
    ) -> XStructuredResult[T]:
        """Asynchronously invoke and parse the wrapped Runnable."""
        raw = await self._runnable.ainvoke(
            self._prepare_input(input),
            config=config,
            **kwargs,
        )
        return await self._aparse_output(raw, config=config)

    def stream(
        self,
        input: Input,  # noqa: A002 - LangChain Runnable API compatibility
        config: RunnableConfig | None = None,
        **kwargs: Any | None,
    ) -> Iterator[StreamEvent[T]]:
        """Yield ordered protocol events from the wrapped Runnable's stream."""
        if self.multiple_envelopes:
            raise ValueError("Streaming multiple named envelopes is not supported")
        decoder = StreamDecoder(self._parser, self.envelope)
        raw_chunks: list[Any] = []
        raw_text_parts: list[str] = []
        structured: T | None = None
        structured_found = False

        for raw_chunk in self._runnable.stream(self._prepare_input(input), config=config, **kwargs):
            raw_chunks.append(raw_chunk)
            text = output_text(raw_chunk)
            raw_text_parts.append(text)
            for event in decoder.feed(text):
                if event.kind is StreamEventKind.STRUCTURED_END:
                    structured = event.structured
                    structured_found = True
                yield event

        yield from decoder.finalize()
        if not structured_found:
            raise RuntimeError("Streaming decoder completed without a structured value")
        parsed = self._parser.parse("".join(raw_text_parts))
        result = self._build_result(
            raw=tuple(raw_chunks),
            raw_text="".join(raw_text_parts),
            content=decoder.text,
            structured=cast(T, structured),
            json_text=parsed.json_text,
            recovered=parsed.recovered,
            schema_name=parsed.schema_name,
            repaired=parsed.repaired,
            repair_attempt_count=parsed.repair_attempt_count,
            stream_completed=True,
        )
        yield StreamEvent(
            kind=StreamEventKind.RESULT,
            sequence=decoder.next_sequence,
            result=result,
        )

    async def astream(
        self,
        input: Input,  # noqa: A002 - LangChain Runnable API compatibility
        config: RunnableConfig | None = None,
        **kwargs: Any | None,
    ) -> AsyncIterator[StreamEvent[T]]:
        """Asynchronously yield ordered protocol events."""
        if self.multiple_envelopes:
            raise ValueError("Streaming multiple named envelopes is not supported")
        decoder = StreamDecoder(self._parser, self.envelope)
        raw_chunks: list[Any] = []
        raw_text_parts: list[str] = []
        structured: T | None = None
        structured_found = False

        async for raw_chunk in self._runnable.astream(
            self._prepare_input(input), config=config, **kwargs
        ):
            raw_chunks.append(raw_chunk)
            text = output_text(raw_chunk)
            raw_text_parts.append(text)
            for event in decoder.feed(text):
                if event.kind is StreamEventKind.STRUCTURED_END:
                    structured = event.structured
                    structured_found = True
                yield event

        for event in decoder.finalize():
            yield event
        if not structured_found:
            raise RuntimeError("Streaming decoder completed without a structured value")
        parsed = self._parser.parse("".join(raw_text_parts))
        result = self._build_result(
            raw=tuple(raw_chunks),
            raw_text="".join(raw_text_parts),
            content=decoder.text,
            structured=cast(T, structured),
            json_text=parsed.json_text,
            recovered=parsed.recovered,
            schema_name=parsed.schema_name,
            repaired=parsed.repaired,
            repair_attempt_count=parsed.repair_attempt_count,
            stream_completed=True,
        )
        yield StreamEvent(
            kind=StreamEventKind.RESULT,
            sequence=decoder.next_sequence,
            result=result,
        )

    def _prepare_input(self, value: Input) -> Input:
        if not self.inject_instructions:
            return value
        if isinstance(value, str):
            return cast(Input, f"{value}\n\n{self.instructions}")
        if isinstance(value, PromptValue):
            messages = [
                SystemMessage(content=self.instructions),
                *value.to_messages(),
            ]
            return cast(Input, messages)
        if (
            isinstance(value, Sequence)
            and not isinstance(value, (str, bytes))
            and all(isinstance(item, BaseMessage) for item in value)
        ):
            return cast(
                Input,
                [SystemMessage(content=self.instructions), *value],
            )
        return value

    def _parse_output(
        self, raw: Any, *, config: RunnableConfig | None = None
    ) -> XStructuredResult[T]:
        raw_text = output_text(raw)
        started = perf_counter()
        try:
            parsed = self._parser.parse(raw_text)
        except ParseError as error:
            if self._repairer is None:
                raise
            parsed = self._repairer.repair(raw_text, error, config=config)
        parse_duration = perf_counter() - started
        return self._build_result(
            raw=raw,
            raw_text=raw_text,
            content=_natural_content(raw_text, self.envelope),
            structured=parsed.value,
            json_text=parsed.json_text,
            recovered=parsed.recovered,
            schema_name=parsed.schema_name,
            repaired=parsed.repaired,
            repair_attempt_count=parsed.repair_attempt_count,
            parse_duration=parse_duration,
        )

    async def _aparse_output(
        self, raw: Any, *, config: RunnableConfig | None = None
    ) -> XStructuredResult[T]:
        raw_text = output_text(raw)
        started = perf_counter()
        try:
            parsed = self._parser.parse(raw_text)
        except ParseError as error:
            if self._repairer is None:
                raise
            parsed = await self._repairer.arepair(raw_text, error, config=config)
        parse_duration = perf_counter() - started
        return self._build_result(
            raw=raw,
            raw_text=raw_text,
            content=_natural_content(raw_text, self.envelope),
            structured=parsed.value,
            json_text=parsed.json_text,
            recovered=parsed.recovered,
            schema_name=parsed.schema_name,
            repaired=parsed.repaired,
            repair_attempt_count=parsed.repair_attempt_count,
            parse_duration=parse_duration,
        )

    def _build_result(
        self,
        *,
        raw: Any,
        raw_text: str,
        content: str,
        structured: T,
        json_text: str,
        recovered: bool,
        schema_name: str | None = None,
        repaired: bool = False,
        repair_attempt_count: int = 0,
        stream_completed: bool = True,
        parse_duration: float = 0.0,
    ) -> XStructuredResult[T]:
        envelope_count = raw_text.count(self.envelope.start)
        metadata: dict[str, Any] = {
            "schema_fingerprint": self.schema_fingerprint,
            "envelope_detected": envelope_count > 0,
            "envelope_count": envelope_count,
            "parse_duration": parse_duration,
            "validation_duration": parse_duration,
            "repair_attempted": repaired,
            "repair_attempt_count": repair_attempt_count,
            "stream_completed": stream_completed,
        }
        if isinstance(raw, BaseMessage):
            metadata.update(
                {
                    "message_id": raw.id,
                    "message_name": raw.name,
                    "message_type": raw.type,
                    "response_metadata": dict(raw.response_metadata),
                }
            )
            usage_metadata = getattr(raw, "usage_metadata", None)
            if usage_metadata is not None:
                metadata["usage_metadata"] = dict(usage_metadata)
        return XStructuredResult(
            content=content,
            structured=structured,
            raw=raw,
            raw_text=raw_text,
            json_text=json_text,
            recovered=recovered,
            metadata=MappingProxyType(metadata),
            schema_name=schema_name,
            repaired=repaired,
            repair_attempt_count=repair_attempt_count,
        )


@overload
def with_xstructured_output(
    runnable: Runnable[Input, Any],
    schema: SchemaTarget | NamedSchemaTargets | NamedSchemas,
    *,
    multiple: Literal[True],
    envelope: EnvelopeSpec | None = None,
    parser_config: ParserConfig | None = None,
    inject_instructions: bool = True,
    repair: Runnable[Any, Any] | None = None,
    repair_config: RepairConfig | None = None,
) -> XStructuredRunnable[Input, list[T]]: ...


@overload
def with_xstructured_output(
    runnable: Runnable[Input, Any],
    schema: SchemaTarget | NamedSchemaTargets | NamedSchemas,
    *,
    multiple: Literal[False] = False,
    envelope: EnvelopeSpec | None = None,
    parser_config: ParserConfig | None = None,
    inject_instructions: bool = True,
    repair: Runnable[Any, Any] | None = None,
    repair_config: RepairConfig | None = None,
) -> XStructuredRunnable[Input, T]: ...


def with_xstructured_output(
    runnable: Runnable[Input, Any],
    schema: SchemaTarget | NamedSchemaTargets | NamedSchemas,
    *,
    envelope: EnvelopeSpec | None = None,
    parser_config: ParserConfig | None = None,
    multiple: bool = False,
    multiple_envelopes: bool = False,
    inject_instructions: bool = True,
    repair: Runnable[Any, Any] | None = None,
    repair_config: RepairConfig | None = None,
) -> XStructuredRunnable[Input, T | list[T]]:
    """Wrap a Runnable with instruction injection and xstructured decoding.

    *schema* may be a single schema target, or a named set of schema targets
    (`Mapping[str, SchemaTarget]` or `NamedSchemas`) to validate the response
    against one of several allowed shapes -- see `xstructured.schema.named`.

    *repair* is an optional, strictly opt-in `Runnable` invoked, bounded by
    `repair_config.max_attempts` (default 1), to ask a model to fix a
    response that failed schema validation. It is never invoked unless
    explicitly supplied here; see `xstructured.langchain.repair` for the
    bounded retry contract.
    """
    return XStructuredRunnable(
        runnable,
        schema,
        envelope=envelope,
        parser_config=parser_config,
        multiple=multiple,
        multiple_envelopes=multiple_envelopes,
        inject_instructions=inject_instructions,
        repair=repair,
        repair_config=repair_config,
    )


def _natural_content(text: str, envelope: EnvelopeSpec) -> str:
    named_pattern = re.compile(
        r"<xstructured name=\"[A-Za-z0-9_.-]+\">.*?</xstructured>", re.DOTALL
    )
    if named_pattern.search(text):
        return named_pattern.sub("", text)
    start_at = text.find(envelope.start)
    if start_at < 0:
        return text
    from xstructured.envelope import EnvelopeScanner

    scanner = EnvelopeScanner(envelope)
    scanner.feed(text)
    if not scanner.complete or scanner.payload is None:
        return text[:start_at]
    end_at = start_at + len(envelope.start) + len(scanner.payload)
    return text[:start_at] + text[end_at + len(envelope.end) :]
