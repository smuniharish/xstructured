"""LangChain Runnable integration."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from time import perf_counter
from types import MappingProxyType
from typing import Any, Literal, cast, overload

from langchain_core.callbacks import (
    AsyncCallbackManagerForChainRun,
    CallbackManagerForChainRun,
)
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.runnables.config import patch_config
from pydantic import TypeAdapter

from xstructured.core.config import ParserConfig, RepairConfig
from xstructured.core.errors import LimitExceededError, ParseError
from xstructured.core.result import ParseResult, XStructuredResult
from xstructured.envelope.spec import EnvelopeSpec
from xstructured.parser.parser import StructuredParser
from xstructured.schema.fingerprint import fingerprint_schema
from xstructured.schema.instructions import schema_instructions
from xstructured.schema.introspection import SchemaInfo, SchemaTarget
from xstructured.schema.named import NamedSchemas, NamedSchemaTargets
from xstructured.streaming.decoder import StreamDecoder
from xstructured.streaming.events import StreamEvent, StreamEventKind

from ._messages import ChunkAccumulator, inject_instructions, output_text
from ._repair import Repairer

__all__ = ["XStructuredRunnable", "with_xstructured_output"]

_REPAIR_TAG = "xstructured:repair"
_MISSING: Any = object()


class XStructuredRunnable[InputT, T](Runnable[InputT, XStructuredResult[T]]):
    """A Runnable that adds schema instructions and returns validated results.

    Use `with_xstructured_output` to create one. The wrapper injects instructions into
    the input, runs the wrapped Runnable, extracts the envelope from its output, and
    validates the payload. It is traced as its own run, with the wrapped Runnable (and
    the repair Runnable, when used) as child runs.

    - `invoke`, `ainvoke`, `batch` and `abatch` return `XStructuredResult` values.
    - `stream` and `astream` yield ordered `StreamEvent` values that end with one
      `RESULT` event.
    - Inside a composed chain (`transform`/`atransform`) the wrapper behaves like any
      Runnable and emits its final `XStructuredResult`, so downstream steps receive the
      same value as with `invoke`.

    Args:
        runnable: A Runnable whose output is a string or a `BaseMessage`.
        schema: A schema target, a `SchemaInfo`, or named schemas.
        envelope: Envelope delimiters. Defaults to ``<xstructured>`` / ``</xstructured>``.
        parser_config: Limits and recovery settings. An envelope is always required.
        multiple: Expect a JSON array of values.
        multiple_envelopes: Expect one named envelope per applicable named schema.
        inject_instructions: Add the instructions to the input. Disable it to place
            `instructions` in your own prompt.
        repair: Optional Runnable asked to correct responses that fail validation.
        repair_config: Bounds for *repair*.

    Raises:
        ValueError: If *repair_config* is given without *repair*, or options conflict.
        SchemaError: If the schema is invalid.
        EnvelopeError: If the envelope cannot express the requested mode.
    """

    def __init__(
        self,
        runnable: Runnable[InputT, Any],
        schema: SchemaTarget | SchemaInfo | NamedSchemaTargets | NamedSchemas,
        *,
        envelope: EnvelopeSpec | None = None,
        parser_config: ParserConfig | None = None,
        multiple: bool = False,
        multiple_envelopes: bool = False,
        inject_instructions: bool = True,
        repair: Runnable[Any, Any] | None = None,
        repair_config: RepairConfig | None = None,
    ) -> None:
        if repair_config is not None and repair is None:
            raise ValueError("repair_config requires a repair Runnable")
        envelope = envelope or EnvelopeSpec()
        config = parser_config or ParserConfig()
        if not config.require_envelope:
            config = config.model_copy(update={"require_envelope": True})
        parser: StructuredParser[T] = StructuredParser(
            schema,
            config=config,
            envelope=envelope,
            multiple=multiple,
            multiple_envelopes=multiple_envelopes,
        )
        self._runnable = runnable
        self._parser = parser
        self._envelope = envelope
        self._instructions = schema_instructions(
            parser.schema,
            envelope=envelope,
            multiple=multiple,
            multiple_envelopes=multiple_envelopes,
        )
        self._schema_fingerprint = fingerprint_schema(parser.schema)
        self._inject_instructions = inject_instructions
        self._repairer: Repairer[T] | None = (
            None
            if repair is None
            else Repairer(
                parser,
                repair,
                repair_config or RepairConfig(),
                self._instructions,
            )
        )

    def __repr__(self) -> str:
        return f"XStructuredRunnable({self._runnable!r})"

    @property
    def runnable(self) -> Runnable[InputT, Any]:
        """The wrapped Runnable."""
        return self._runnable

    @property
    def parser(self) -> StructuredParser[T]:
        """The parser used for every response."""
        return self._parser

    @property
    def envelope(self) -> EnvelopeSpec:
        """The envelope delimiters."""
        return self._envelope

    @property
    def instructions(self) -> str:
        """The instructions added to inputs, or to place in your own prompt."""
        return self._instructions

    @property
    def schema_fingerprint(self) -> str:
        """SHA-256 fingerprint of the schema (see `fingerprint_schema`)."""
        return self._schema_fingerprint

    @property
    def InputType(self) -> type[InputT]:  # noqa: N802 - LangChain API name
        """The wrapped Runnable's input type."""
        return self._runnable.InputType

    @property
    def OutputType(self) -> type[XStructuredResult[T]]:  # noqa: N802 - LangChain API name
        """`XStructuredResult`."""
        return cast("type[XStructuredResult[T]]", XStructuredResult)

    def invoke(
        self,
        input: InputT,  # noqa: A002 - LangChain API name
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> XStructuredResult[T]:
        """Run the wrapped Runnable and return the validated result.

        Raises:
            TypeError: If the input cannot carry instructions.
            ParseError: If the response does not validate (including `RecoveryError`,
                `LimitExceededError` and `RepairError`).
        """
        return self._call_with_config(self._invoke, input, config, **kwargs)

    async def ainvoke(
        self,
        input: InputT,  # noqa: A002 - LangChain API name
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> XStructuredResult[T]:
        """Asynchronously run the wrapped Runnable and return the validated result.

        Raises:
            TypeError: If the input cannot carry instructions.
            ParseError: If the response does not validate.
        """
        return await self._acall_with_config(
            self._ainvoke, input, config, **kwargs
        )

    def stream(  # pyrefly: ignore[bad-override]
        self,
        input: InputT,  # noqa: A002 - LangChain API name
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Iterator[StreamEvent[T]]:
        """Stream ordered protocol events, ending with one `RESULT` event.

        Raises:
            TypeError: If the input cannot carry instructions.
            ValueError: If the wrapper expects named envelopes.
            ParseError: If the response does not validate.
        """
        transformer = cast(
            "Callable[..., Iterator[XStructuredResult[T]]]", self._stream_events
        )
        events = self._transform_stream_with_config(
            iter([input]), transformer, config, **kwargs
        )
        yield from cast("Iterator[StreamEvent[T]]", events)

    async def astream(  # pyrefly: ignore[bad-override]
        self,
        input: InputT,  # noqa: A002 - LangChain API name
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent[T]]:
        """Asynchronously stream ordered protocol events, ending with one `RESULT` event.

        Raises:
            TypeError: If the input cannot carry instructions.
            ValueError: If the wrapper expects named envelopes.
            ParseError: If the response does not validate.
        """
        transformer = cast(
            "Callable[..., AsyncIterator[XStructuredResult[T]]]",
            self._astream_events,
        )
        events = self._atransform_stream_with_config(
            _once(input), transformer, config, **kwargs
        )
        async for event in cast("AsyncIterator[StreamEvent[T]]", events):
            yield event

    def transform(
        self,
        input: Iterator[InputT],  # noqa: A002 - LangChain API name
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Iterator[XStructuredResult[T]]:
        """Consume streamed input inside a composed chain and emit the final result."""
        yield from self._transform_stream_with_config(
            input, self._transform_results, config, **kwargs
        )

    async def atransform(
        self,
        input: AsyncIterator[InputT],  # noqa: A002 - LangChain API name
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[XStructuredResult[T]]:
        """Asynchronously consume streamed input and emit the final result."""
        async for result in self._atransform_stream_with_config(
            input, self._atransform_results, config, **kwargs
        ):
            yield result

    def _invoke(
        self,
        input_: InputT,
        run_manager: CallbackManagerForChainRun,
        config: RunnableConfig,
        **kwargs: Any,
    ) -> XStructuredResult[T]:
        raw = self._runnable.invoke(self._prepare(input_), config, **kwargs)
        return self._finish(raw, output_text(raw), run_manager, config)

    async def _ainvoke(
        self,
        input_: InputT,
        run_manager: AsyncCallbackManagerForChainRun,
        config: RunnableConfig,
        **kwargs: Any,
    ) -> XStructuredResult[T]:
        raw = await self._runnable.ainvoke(
            self._prepare(input_), config, **kwargs
        )
        return await self._afinish(raw, output_text(raw), run_manager, config)

    def _stream_events(
        self,
        inputs: Iterator[InputT],
        config: RunnableConfig,
        **kwargs: Any,
    ) -> Iterator[StreamEvent[T]]:
        decoder = StreamDecoder(self._parser)
        chunks = ChunkAccumulator()
        elapsed = 0.0
        for chunk in self._runnable.stream(
            self._prepare(next(inputs)), config, **kwargs
        ):
            text = chunks.add(chunk)
            started = perf_counter()
            events = decoder.feed(text)
            elapsed += perf_counter() - started
            yield from events
        started = perf_counter()
        decoder.finalize()
        elapsed += perf_counter() - started
        yield self._result_event(decoder, chunks, elapsed)

    async def _astream_events(
        self,
        inputs: AsyncIterator[InputT],
        config: RunnableConfig,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent[T]]:
        decoder = StreamDecoder(self._parser)
        chunks = ChunkAccumulator()
        elapsed = 0.0
        prepared = self._prepare(await anext(inputs))
        async for chunk in self._runnable.astream(prepared, config, **kwargs):
            text = chunks.add(chunk)
            started = perf_counter()
            events = decoder.feed(text)
            elapsed += perf_counter() - started
            for event in events:
                yield event
        started = perf_counter()
        decoder.finalize()
        elapsed += perf_counter() - started
        yield self._result_event(decoder, chunks, elapsed)

    def _transform_results(
        self,
        inputs: Iterator[InputT],
        run_manager: CallbackManagerForChainRun,
        config: RunnableConfig,
        **kwargs: Any,
    ) -> Iterator[XStructuredResult[T]]:
        input_ = _fold(inputs)
        if input_ is _MISSING:
            return
        chunks = ChunkAccumulator()
        for chunk in self._runnable.stream(
            self._prepare(input_), config, **kwargs
        ):
            chunks.add(chunk)
        yield self._finish(chunks.output(), chunks.text, run_manager, config)

    async def _atransform_results(
        self,
        inputs: AsyncIterator[InputT],
        run_manager: AsyncCallbackManagerForChainRun,
        config: RunnableConfig,
        **kwargs: Any,
    ) -> AsyncIterator[XStructuredResult[T]]:
        input_ = await _afold(inputs)
        if input_ is _MISSING:
            return
        chunks = ChunkAccumulator()
        async for chunk in self._runnable.astream(
            self._prepare(input_), config, **kwargs
        ):
            chunks.add(chunk)
        yield await self._afinish(
            chunks.output(), chunks.text, run_manager, config
        )

    def _prepare(self, value: Any) -> Any:
        if not self._inject_instructions:
            return value
        return inject_instructions(value, self._instructions)

    def _finish(
        self,
        raw: Any,
        raw_text: str,
        run_manager: CallbackManagerForChainRun,
        config: RunnableConfig,
    ) -> XStructuredResult[T]:
        started = perf_counter()
        try:
            parsed = self._parser.parse(raw_text)
        except ParseError as error:
            repairer = self._repairable(error)
            repair_config = patch_config(
                config, callbacks=run_manager.get_child(_REPAIR_TAG)
            )
            parsed = repairer.repair(raw_text, error, repair_config)
            content = self._parser.strip_envelopes(raw_text)
        else:
            content = _remove_spans(raw_text, parsed.envelope_spans)
        return self._result(
            raw=raw,
            raw_text=raw_text,
            content=content,
            parsed=parsed,
            envelope_count=len(parsed.envelope_spans),
            parse_duration=perf_counter() - started,
        )

    async def _afinish(
        self,
        raw: Any,
        raw_text: str,
        run_manager: AsyncCallbackManagerForChainRun,
        config: RunnableConfig,
    ) -> XStructuredResult[T]:
        started = perf_counter()
        try:
            parsed = self._parser.parse(raw_text)
        except ParseError as error:
            repairer = self._repairable(error)
            repair_config = patch_config(
                config, callbacks=run_manager.get_child(_REPAIR_TAG)
            )
            parsed = await repairer.arepair(raw_text, error, repair_config)
            content = self._parser.strip_envelopes(raw_text)
        else:
            content = _remove_spans(raw_text, parsed.envelope_spans)
        return self._result(
            raw=raw,
            raw_text=raw_text,
            content=content,
            parsed=parsed,
            envelope_count=len(parsed.envelope_spans),
            parse_duration=perf_counter() - started,
        )

    def _repairable(self, error: ParseError) -> Repairer[T]:
        repairer = self._repairer
        if (
            repairer is None
            or not repairer.enabled
            or isinstance(error, LimitExceededError)
        ):
            raise error
        return repairer

    def _result_event(
        self,
        decoder: StreamDecoder[T],
        chunks: ChunkAccumulator,
        elapsed: float,
    ) -> StreamEvent[T]:
        result = self._result(
            raw=chunks.output(),
            raw_text=chunks.text,
            content=decoder.text,
            parsed=decoder.result,
            envelope_count=1,
            parse_duration=elapsed,
        )
        return StreamEvent(
            kind=StreamEventKind.RESULT,
            sequence=decoder.next_sequence,
            result=result,
        )

    def _result(
        self,
        *,
        raw: Any,
        raw_text: str,
        content: str,
        parsed: ParseResult[T],
        envelope_count: int,
        parse_duration: float,
    ) -> XStructuredResult[T]:
        metadata: dict[str, Any] = {
            "schema_fingerprint": self._schema_fingerprint,
            "envelope_count": envelope_count,
            "parse_duration": parse_duration,
        }
        if isinstance(raw, BaseMessage):
            metadata["message_id"] = raw.id
            metadata["response_metadata"] = dict(raw.response_metadata)
            usage = getattr(raw, "usage_metadata", None)
            if usage:
                metadata["usage_metadata"] = dict(usage)
        return XStructuredResult(
            content=content,
            structured=parsed.value,
            raw=raw,
            raw_text=raw_text,
            json_text=parsed.json_text,
            recovered=parsed.recovered,
            schema_name=parsed.schema_name,
            repaired=parsed.repaired,
            repair_attempts=parsed.repair_attempts,
            metadata=MappingProxyType(metadata),
        )


@overload
def with_xstructured_output[InputT, S](
    runnable: Runnable[InputT, Any],
    schema: type[S],
    *,
    envelope: EnvelopeSpec | None = None,
    parser_config: ParserConfig | None = None,
    multiple: Literal[False] = False,
    multiple_envelopes: Literal[False] = False,
    inject_instructions: bool = True,
    repair: Runnable[Any, Any] | None = None,
    repair_config: RepairConfig | None = None,
) -> XStructuredRunnable[InputT, S]: ...


@overload
def with_xstructured_output[InputT, S](
    runnable: Runnable[InputT, Any],
    schema: type[S],
    *,
    envelope: EnvelopeSpec | None = None,
    parser_config: ParserConfig | None = None,
    multiple: Literal[True],
    multiple_envelopes: Literal[False] = False,
    inject_instructions: bool = True,
    repair: Runnable[Any, Any] | None = None,
    repair_config: RepairConfig | None = None,
) -> XStructuredRunnable[InputT, list[S]]: ...


@overload
def with_xstructured_output[InputT, S](
    runnable: Runnable[InputT, Any],
    schema: TypeAdapter[S],
    *,
    envelope: EnvelopeSpec | None = None,
    parser_config: ParserConfig | None = None,
    multiple: Literal[False] = False,
    multiple_envelopes: Literal[False] = False,
    inject_instructions: bool = True,
    repair: Runnable[Any, Any] | None = None,
    repair_config: RepairConfig | None = None,
) -> XStructuredRunnable[InputT, S]: ...


@overload
def with_xstructured_output[InputT, S](
    runnable: Runnable[InputT, Any],
    schema: TypeAdapter[S],
    *,
    envelope: EnvelopeSpec | None = None,
    parser_config: ParserConfig | None = None,
    multiple: Literal[True],
    multiple_envelopes: Literal[False] = False,
    inject_instructions: bool = True,
    repair: Runnable[Any, Any] | None = None,
    repair_config: RepairConfig | None = None,
) -> XStructuredRunnable[InputT, list[S]]: ...


@overload
def with_xstructured_output[InputT](
    runnable: Runnable[InputT, Any],
    schema: NamedSchemaTargets | NamedSchemas,
    *,
    envelope: EnvelopeSpec | None = None,
    parser_config: ParserConfig | None = None,
    multiple: Literal[False] = False,
    multiple_envelopes: Literal[True],
    inject_instructions: bool = True,
    repair: Runnable[Any, Any] | None = None,
    repair_config: RepairConfig | None = None,
) -> XStructuredRunnable[InputT, dict[str, Any]]: ...


@overload
def with_xstructured_output[InputT](
    runnable: Runnable[InputT, Any],
    schema: SchemaTarget | SchemaInfo | NamedSchemaTargets | NamedSchemas,
    *,
    envelope: EnvelopeSpec | None = None,
    parser_config: ParserConfig | None = None,
    multiple: bool = False,
    multiple_envelopes: bool = False,
    inject_instructions: bool = True,
    repair: Runnable[Any, Any] | None = None,
    repair_config: RepairConfig | None = None,
) -> XStructuredRunnable[InputT, Any]: ...


def with_xstructured_output[InputT](
    runnable: Runnable[InputT, Any],
    schema: SchemaTarget | SchemaInfo | NamedSchemaTargets | NamedSchemas,
    *,
    envelope: EnvelopeSpec | None = None,
    parser_config: ParserConfig | None = None,
    multiple: bool = False,
    multiple_envelopes: bool = False,
    inject_instructions: bool = True,
    repair: Runnable[Any, Any] | None = None,
    repair_config: RepairConfig | None = None,
) -> XStructuredRunnable[InputT, Any]:
    """Wrap a Runnable so its output is validated against a Pydantic schema.

    Args:
        runnable: A chat model, chain, or any Runnable whose output is a string or a
            `BaseMessage`.
        schema: A model class, `TypeAdapter`, or annotation; or named schemas as a
            mapping of names to targets.
        envelope: Envelope delimiters. Defaults to ``<xstructured>`` / ``</xstructured>``.
        parser_config: Limits and recovery settings. An envelope is always required.
        multiple: Expect a JSON array; `XStructuredResult.structured` is a list.
        multiple_envelopes: Expect one named envelope per applicable named schema;
            `XStructuredResult.structured` is a dict keyed by name.
        inject_instructions: Add the schema instructions to each input. When disabled,
            include `XStructuredRunnable.instructions` in your own prompt.
        repair: Optional Runnable asked to correct responses that fail validation, after
            conservative recovery. It is never called unless supplied.
        repair_config: Bounds for *repair* (default: one attempt).

    Returns:
        An `XStructuredRunnable`.

    Raises:
        ValueError: If options conflict.
        SchemaError: If the schema is invalid.
        EnvelopeError: If the envelope cannot express the requested mode.

    Example:
        ```python
        from langchain.chat_models import init_chat_model
        from pydantic import BaseModel
        from xstructured import with_xstructured_output


        class Contact(BaseModel):
            name: str
            email: str


        model = init_chat_model("openai:gpt-5-mini")
        extractor = with_xstructured_output(model, Contact)
        result = extractor.invoke("Reach Priya Shah at priya@example.com.")
        print(result.structured, result.content)
        ```
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


def _fold(chunks: Iterator[Any]) -> Any:
    folded = _MISSING
    for chunk in chunks:
        folded = chunk if folded is _MISSING else _add(folded, chunk)
    return folded


async def _afold(chunks: AsyncIterator[Any]) -> Any:
    folded = _MISSING
    async for chunk in chunks:
        folded = chunk if folded is _MISSING else _add(folded, chunk)
    return folded


def _add(left: Any, right: Any) -> Any:
    try:
        return left + right
    except TypeError:
        return right


async def _once[V](value: V) -> AsyncIterator[V]:
    yield value


def _remove_spans(text: str, spans: tuple[tuple[int, int], ...]) -> str:
    parts: list[str] = []
    position = 0
    for start, end in spans:
        parts.append(text[position:start])
        position = end
    parts.append(text[position:])
    return "".join(parts)
