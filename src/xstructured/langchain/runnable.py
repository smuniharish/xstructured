"""LangChain Runnable integration."""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator, Callable, Iterator, Mapping
from time import perf_counter
from typing import Any, Literal, cast, overload

from langchain_core.callbacks import (
    AsyncCallbackManagerForChainRun,
    CallbackManagerForChainRun,
)
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.runnables.config import patch_config
from pydantic import TypeAdapter

from xstructured.contracts import (
    AttributeValue,
    InstructionInjector,
    InstructionRenderer,
    JsonDecoder,
    Observation,
    Observer,
    OutputTextExtractor,
    RecoveryStrategy,
    RepairPromptBuilder,
    require_instance,
)
from xstructured.core.config import ParserConfig, RepairConfig
from xstructured.core.errors import LimitExceededError, ParseError
from xstructured.core.result import ParseResult, XStructuredResult
from xstructured.envelope.spec import EnvelopeSpec
from xstructured.parser.parser import StructuredParser
from xstructured.schema.fingerprint import fingerprint_schema
from xstructured.schema.instructions import schema_instructions
from xstructured.schema.introspection import SchemaInfo, SchemaTarget
from xstructured.schema.named import NamedSchemas, NamedSchemaTargets
from xstructured.schema.options import SchemaOptions
from xstructured.streaming.decoder import StreamDecoder
from xstructured.streaming.events import StreamEvent, StreamEventKind

from ._messages import (
    ChunkAccumulator,
    MessageInstructionInjector,
    MessageTextExtractor,
)
from ._repair import DefaultRepairPrompt, Repairer
from ._shared import (
    build_result,
    observe,
    remove_spans,
    result_attributes,
    validation_context,
)

__all__ = ["XStructuredRunnable", "with_xstructured_output"]

_REPAIR_TAG = "xstructured:repair"
_MISSING: Any = object()


class XStructuredRunnable[InputT, T](Runnable[InputT, XStructuredResult[T]]):
    """A Runnable that adds schema instructions and returns validated results.

    Use `with_xstructured_output` to create one. The wrapper injects instructions into
    the input, runs the wrapped Runnable, extracts the envelope from its output, and
    validates the payload. It is traced as its own run, with the wrapped Runnable (and
    the repair Runnable, when used) as child runs.

    - `ainvoke`, `abatch`, `invoke` and `batch` return `XStructuredResult` values.
    - `astream` and `stream` yield ordered `StreamEvent` values that end with one
      `RESULT` event.
    - Inside a composed chain (`atransform`/`transform`) the wrapper behaves like any
      Runnable and emits its final `XStructuredResult`, so downstream steps receive the
      same value as with `ainvoke`.

    A LangGraph graph, including a LangChain or Deep Agents agent, can be wrapped
    directly: its state input gets the instructions, its last AI message is parsed,
    and it streams in ``messages`` mode unless *stream_mode* is passed.

    Set ``config["configurable"]["xstructured_context"]`` to pass a Pydantic
    validation context for one call.

    Args:
        runnable: A Runnable whose output is a string, a `BaseMessage`, or a state
            mapping with messages.
        schema: A schema target, a `SchemaInfo`, or named schemas.
        envelope: Envelope delimiters. Defaults to ``<xstructured>`` / ``</xstructured>``.
        parser_config: Limits and recovery settings. An envelope is always required.
        multiple: Expect a JSON array of values.
        multiple_envelopes: Expect one named envelope per applicable named schema.
        inject_instructions: Add the instructions to the input. Disable it to place
            `instructions` in your own prompt.
        repair: Optional Runnable asked to correct responses that fail validation.
        repair_config: Bounds for *repair*.
        schema_options: Pydantic configuration and JSON Schema generation options.
        renderer: Renders the instructions (default `DefaultInstructionRenderer`).
        injector: Adds the instructions to the input (default
            `MessageInstructionInjector`).
        extractor: Reads response text from outputs and stream chunks (default
            `MessageTextExtractor`).
        recovery: Chooses the substrings tried as JSON (default
            `ConservativeRecovery` built from *parser_config*).
        decoder: Decodes each candidate (default `StrictJsonDecoder`).
        repair_prompt: Builds the input of *repair* (default `DefaultRepairPrompt`).
        observer: Receives one observation per call, for telemetry.
        name: The run name shown in traces.

    Raises:
        ValueError: If repair options are given without *repair*, or options conflict.
        TypeError: If an extension point does not subclass its base class.
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
        schema_options: SchemaOptions | None = None,
        renderer: InstructionRenderer | None = None,
        injector: InstructionInjector | None = None,
        extractor: OutputTextExtractor | None = None,
        recovery: RecoveryStrategy | None = None,
        decoder: JsonDecoder | None = None,
        repair_prompt: RepairPromptBuilder | None = None,
        observer: Observer | None = None,
        name: str | None = None,
    ) -> None:
        if repair is None and (
            repair_config is not None or repair_prompt is not None
        ):
            raise ValueError(
                "repair_config and repair_prompt require a repair Runnable"
            )
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
            schema_options=schema_options,
            recovery=recovery,
            decoder=decoder,
        )
        self.name = name
        self._runnable = runnable
        self._parser = parser
        self._envelope = envelope
        self._instructions = schema_instructions(
            parser.schema,
            envelope=envelope,
            multiple=multiple,
            multiple_envelopes=multiple_envelopes,
            renderer=renderer,
        )
        self._schema_fingerprint = fingerprint_schema(parser.schema)
        self._inject_instructions = inject_instructions
        self._injector = (
            MessageInstructionInjector()
            if injector is None
            else require_instance(injector, InstructionInjector, "injector")
        )
        self._extractor = (
            MessageTextExtractor()
            if extractor is None
            else require_instance(extractor, OutputTextExtractor, "extractor")
        )
        self._observer = (
            None
            if observer is None
            else require_instance(observer, Observer, "observer")
        )
        self._attributes: Mapping[str, AttributeValue] = {
            "xstructured.name": self.get_name(),
            "xstructured.schema_fingerprint": self._schema_fingerprint,
            "xstructured.multiple": multiple,
            "xstructured.multiple_envelopes": multiple_envelopes,
        }
        self._repairer: Repairer[T] | None = (
            None
            if repair is None
            else Repairer(
                parser,
                repair,
                repair_config or RepairConfig(),
                self._instructions,
                prompt=(
                    DefaultRepairPrompt()
                    if repair_prompt is None
                    else require_instance(
                        repair_prompt, RepairPromptBuilder, "repair_prompt"
                    )
                ),
                extractor=self._extractor,
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
    def injector(self) -> InstructionInjector:
        """The instruction injector."""
        return self._injector

    @property
    def extractor(self) -> OutputTextExtractor:
        """The output text extractor."""
        return self._extractor

    @property
    def observer(self) -> Observer | None:
        """The telemetry observer, if any."""
        return self._observer

    @property
    def InputType(self) -> type[InputT]:  # noqa: N802 - LangChain API name
        """The wrapped Runnable's input type."""
        return self._runnable.InputType

    @property
    def OutputType(self) -> type[XStructuredResult[T]]:  # noqa: N802 - LangChain API name
        """`XStructuredResult`."""
        return cast("type[XStructuredResult[T]]", XStructuredResult)

    async def ainvoke(
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
        return await self._acall_with_config(
            self._ainvoke, input, config, **kwargs
        )

    def invoke(
        self,
        input: InputT,  # noqa: A002 - LangChain API name
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> XStructuredResult[T]:
        """Synchronous `ainvoke`, for code that cannot await.

        Raises:
            TypeError: If the input cannot carry instructions.
            ParseError: If the response does not validate.
        """
        return self._call_with_config(self._invoke, input, config, **kwargs)

    async def astream(  # pyrefly: ignore[bad-override]
        self,
        input: InputT,  # noqa: A002 - LangChain API name
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent[T]]:
        """Stream ordered protocol events, ending with one `RESULT` event.

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

    def stream(  # pyrefly: ignore[bad-override]
        self,
        input: InputT,  # noqa: A002 - LangChain API name
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Iterator[StreamEvent[T]]:
        """Synchronous `astream`, for code that cannot await.

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

    async def atransform(
        self,
        input: AsyncIterator[InputT],  # noqa: A002 - LangChain API name
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[XStructuredResult[T]]:
        """Consume streamed input inside a composed chain and emit the final result."""
        async for result in self._atransform_stream_with_config(
            input, self._atransform_results, config, **kwargs
        ):
            yield result

    def transform(
        self,
        input: Iterator[InputT],  # noqa: A002 - LangChain API name
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Iterator[XStructuredResult[T]]:
        """Synchronous `atransform`, for code that cannot await."""
        yield from self._transform_stream_with_config(
            input, self._transform_results, config, **kwargs
        )

    async def _ainvoke(
        self,
        input_: InputT,
        run_manager: AsyncCallbackManagerForChainRun,
        config: RunnableConfig,
        **kwargs: Any,
    ) -> XStructuredResult[T]:
        observation = self._observe("invoke")
        try:
            raw = await self._runnable.ainvoke(
                self._prepare(input_), config, **kwargs
            )
            result = await self._afinish(
                raw, self._extractor.text(raw), run_manager, config
            )
        except BaseException as exc:
            observation.fail(exc)
            raise
        observation.succeed(result_attributes(result))
        return result

    def _invoke(
        self,
        input_: InputT,
        run_manager: CallbackManagerForChainRun,
        config: RunnableConfig,
        **kwargs: Any,
    ) -> XStructuredResult[T]:
        observation = self._observe("invoke")
        try:
            raw = self._runnable.invoke(self._prepare(input_), config, **kwargs)
            result = self._finish(
                raw, self._extractor.text(raw), run_manager, config
            )
        except BaseException as exc:
            observation.fail(exc)
            raise
        observation.succeed(result_attributes(result))
        return result

    async def _astream_events(
        self,
        inputs: AsyncIterator[InputT],
        config: RunnableConfig,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent[T]]:
        observation = self._observe("stream")
        try:
            decoder = self._stream_decoder(config)
            chunks = ChunkAccumulator(self._extractor)
            elapsed = 0.0
            prepared = self._prepare(await anext(inputs))
            async for chunk in self._runnable.astream(
                prepared, config, **self._stream_kwargs(kwargs)
            ):
                text = chunks.add(chunk)
                started = perf_counter()
                events = decoder.feed(text)
                elapsed += perf_counter() - started
                for event in events:
                    yield event
            started = perf_counter()
            decoder.finalize()
            elapsed += perf_counter() - started
            event = self._result_event(decoder, chunks, elapsed)
        except BaseException as exc:
            observation.fail(exc)
            raise
        observation.succeed(result_attributes(cast("Any", event.result)))
        yield event

    def _stream_events(
        self,
        inputs: Iterator[InputT],
        config: RunnableConfig,
        **kwargs: Any,
    ) -> Iterator[StreamEvent[T]]:
        observation = self._observe("stream")
        try:
            decoder = self._stream_decoder(config)
            chunks = ChunkAccumulator(self._extractor)
            elapsed = 0.0
            for chunk in self._runnable.stream(
                self._prepare(next(inputs)),
                config,
                **self._stream_kwargs(kwargs),
            ):
                text = chunks.add(chunk)
                started = perf_counter()
                events = decoder.feed(text)
                elapsed += perf_counter() - started
                yield from events
            started = perf_counter()
            decoder.finalize()
            elapsed += perf_counter() - started
            event = self._result_event(decoder, chunks, elapsed)
        except BaseException as exc:
            observation.fail(exc)
            raise
        observation.succeed(result_attributes(cast("Any", event.result)))
        yield event

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
        observation = self._observe("transform")
        try:
            chunks = ChunkAccumulator(self._extractor)
            async for chunk in self._runnable.astream(
                self._prepare(input_), config, **self._stream_kwargs(kwargs)
            ):
                chunks.add(chunk)
            result = await self._afinish(
                chunks.output(), chunks.text, run_manager, config
            )
        except BaseException as exc:
            observation.fail(exc)
            raise
        observation.succeed(result_attributes(result))
        yield result

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
        observation = self._observe("transform")
        try:
            chunks = ChunkAccumulator(self._extractor)
            for chunk in self._runnable.stream(
                self._prepare(input_), config, **self._stream_kwargs(kwargs)
            ):
                chunks.add(chunk)
            result = self._finish(
                chunks.output(), chunks.text, run_manager, config
            )
        except BaseException as exc:
            observation.fail(exc)
            raise
        observation.succeed(result_attributes(result))
        yield result

    def _observe(self, operation: str) -> Observation:
        return observe(self._observer, operation, self._attributes)

    def _stream_decoder(self, config: RunnableConfig) -> StreamDecoder[T]:
        return StreamDecoder(self._parser, context=validation_context(config))

    def _stream_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        if "stream_mode" in kwargs or not _is_graph(self._runnable):
            return kwargs
        return {**kwargs, "stream_mode": "messages"}

    def _prepare(self, value: Any) -> Any:
        if not self._inject_instructions:
            return value
        return self._injector.inject(value, self._instructions)

    async def _afinish(
        self,
        raw: Any,
        raw_text: str,
        run_manager: AsyncCallbackManagerForChainRun,
        config: RunnableConfig,
    ) -> XStructuredResult[T]:
        started = perf_counter()
        context = validation_context(config)
        try:
            parsed = self._parser.parse(raw_text, context=context)
        except ParseError as error:
            repairer = self._repairable(error)
            repair_config = patch_config(
                config, callbacks=run_manager.get_child(_REPAIR_TAG)
            )
            parsed = await repairer.arepair(
                raw_text, error, repair_config, context=context
            )
            content = self._parser.strip_envelopes(raw_text)
        else:
            content = remove_spans(raw_text, parsed.envelope_spans)
        return self._result(raw, raw_text, content, parsed, started)

    def _finish(
        self,
        raw: Any,
        raw_text: str,
        run_manager: CallbackManagerForChainRun,
        config: RunnableConfig,
    ) -> XStructuredResult[T]:
        started = perf_counter()
        context = validation_context(config)
        try:
            parsed = self._parser.parse(raw_text, context=context)
        except ParseError as error:
            repairer = self._repairable(error)
            repair_config = patch_config(
                config, callbacks=run_manager.get_child(_REPAIR_TAG)
            )
            parsed = repairer.repair(
                raw_text, error, repair_config, context=context
            )
            content = self._parser.strip_envelopes(raw_text)
        else:
            content = remove_spans(raw_text, parsed.envelope_spans)
        return self._result(raw, raw_text, content, parsed, started)

    def _repairable(self, error: ParseError) -> Repairer[T]:
        repairer = self._repairer
        if (
            repairer is None
            or not repairer.enabled
            or isinstance(error, LimitExceededError)
        ):
            raise error
        return repairer

    def _result(
        self,
        raw: Any,
        raw_text: str,
        content: str,
        parsed: ParseResult[T],
        started: float,
    ) -> XStructuredResult[T]:
        return build_result(
            fingerprint=self._schema_fingerprint,
            raw=raw,
            raw_text=raw_text,
            content=content,
            parsed=parsed,
            envelope_count=len(parsed.envelope_spans),
            parse_duration=perf_counter() - started,
        )

    def _result_event(
        self,
        decoder: StreamDecoder[T],
        chunks: ChunkAccumulator,
        elapsed: float,
    ) -> StreamEvent[T]:
        result = build_result(
            fingerprint=self._schema_fingerprint,
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
    schema_options: SchemaOptions | None = None,
    renderer: InstructionRenderer | None = None,
    injector: InstructionInjector | None = None,
    extractor: OutputTextExtractor | None = None,
    recovery: RecoveryStrategy | None = None,
    decoder: JsonDecoder | None = None,
    repair_prompt: RepairPromptBuilder | None = None,
    observer: Observer | None = None,
    name: str | None = None,
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
    schema_options: SchemaOptions | None = None,
    renderer: InstructionRenderer | None = None,
    injector: InstructionInjector | None = None,
    extractor: OutputTextExtractor | None = None,
    recovery: RecoveryStrategy | None = None,
    decoder: JsonDecoder | None = None,
    repair_prompt: RepairPromptBuilder | None = None,
    observer: Observer | None = None,
    name: str | None = None,
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
    schema_options: SchemaOptions | None = None,
    renderer: InstructionRenderer | None = None,
    injector: InstructionInjector | None = None,
    extractor: OutputTextExtractor | None = None,
    recovery: RecoveryStrategy | None = None,
    decoder: JsonDecoder | None = None,
    repair_prompt: RepairPromptBuilder | None = None,
    observer: Observer | None = None,
    name: str | None = None,
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
    schema_options: SchemaOptions | None = None,
    renderer: InstructionRenderer | None = None,
    injector: InstructionInjector | None = None,
    extractor: OutputTextExtractor | None = None,
    recovery: RecoveryStrategy | None = None,
    decoder: JsonDecoder | None = None,
    repair_prompt: RepairPromptBuilder | None = None,
    observer: Observer | None = None,
    name: str | None = None,
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
    schema_options: SchemaOptions | None = None,
    renderer: InstructionRenderer | None = None,
    injector: InstructionInjector | None = None,
    extractor: OutputTextExtractor | None = None,
    recovery: RecoveryStrategy | None = None,
    decoder: JsonDecoder | None = None,
    repair_prompt: RepairPromptBuilder | None = None,
    observer: Observer | None = None,
    name: str | None = None,
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
    schema_options: SchemaOptions | None = None,
    renderer: InstructionRenderer | None = None,
    injector: InstructionInjector | None = None,
    extractor: OutputTextExtractor | None = None,
    recovery: RecoveryStrategy | None = None,
    decoder: JsonDecoder | None = None,
    repair_prompt: RepairPromptBuilder | None = None,
    observer: Observer | None = None,
    name: str | None = None,
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
    schema_options: SchemaOptions | None = None,
    renderer: InstructionRenderer | None = None,
    injector: InstructionInjector | None = None,
    extractor: OutputTextExtractor | None = None,
    recovery: RecoveryStrategy | None = None,
    decoder: JsonDecoder | None = None,
    repair_prompt: RepairPromptBuilder | None = None,
    observer: Observer | None = None,
    name: str | None = None,
) -> XStructuredRunnable[InputT, Any]:
    """Wrap a Runnable so its output is validated against a Pydantic schema.

    Args:
        runnable: A chat model, chain, LangGraph graph, agent, or any Runnable whose
            output is a string, a `BaseMessage`, or a state mapping with messages.
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
        schema_options: Pydantic configuration and JSON Schema generation options.
        renderer: An `InstructionRenderer` for the instructions.
        injector: An `InstructionInjector` that adds instructions to the input.
        extractor: An `OutputTextExtractor` that reads outputs and stream chunks.
        recovery: A `RecoveryStrategy` choosing the substrings tried as JSON.
        decoder: A `JsonDecoder` for each candidate.
        repair_prompt: A `RepairPromptBuilder` for the input of *repair*.
        observer: An `Observer` receiving one observation per call.
        name: The run name shown in traces.

    Returns:
        An `XStructuredRunnable`.

    Raises:
        ValueError: If options conflict.
        TypeError: If an extension point does not subclass its base class.
        SchemaError: If the schema is invalid.
        EnvelopeError: If the envelope cannot express the requested mode.

    Example:
        ```python
        import asyncio

        from langchain.chat_models import init_chat_model
        from pydantic import BaseModel
        from xstructured import with_xstructured_output


        class Contact(BaseModel):
            name: str
            email: str


        async def main() -> None:
            model = init_chat_model("openai:gpt-5-mini")
            extractor = with_xstructured_output(model, Contact)
            result = await extractor.ainvoke(
                "Reach Priya Shah at priya@example.com."
            )
            print(result.structured, result.content)


        asyncio.run(main())
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
        schema_options=schema_options,
        renderer=renderer,
        injector=injector,
        extractor=extractor,
        recovery=recovery,
        decoder=decoder,
        repair_prompt=repair_prompt,
        observer=observer,
        name=name,
    )


def _is_graph(runnable: Runnable[Any, Any]) -> bool:
    pregel = sys.modules.get("langgraph.pregel")
    return pregel is not None and isinstance(runnable, pregel.Pregel)


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
