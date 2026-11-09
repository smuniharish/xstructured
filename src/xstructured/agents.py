"""LangChain agent middleware (requires the ``agents`` extra).

`XStructuredMiddleware` gives `langchain.agents.create_agent` and
`deepagents.create_deep_agent` agents a validated final answer without tool
calling or provider-native structured output. Install it with
``pip install "xstructured[agents]"``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from time import perf_counter
from typing import Any, cast, override

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.runnables.config import ensure_config

from .contracts import (
    AttributeValue,
    InstructionRenderer,
    JsonDecoder,
    Observation,
    Observer,
    OutputTextExtractor,
    RecoveryStrategy,
    RepairPromptBuilder,
    require_instance,
)
from .core.config import ParserConfig, RepairConfig
from .core.errors import LimitExceededError, ParseError
from .core.result import ParseResult, XStructuredResult
from .envelope.spec import EnvelopeSpec
from .langchain._messages import MessageTextExtractor, with_system_instructions
from .langchain._repair import DefaultRepairPrompt, exhausted_error
from .langchain._shared import (
    build_result,
    observe,
    remove_spans,
    result_attributes,
    validation_context,
)
from .parser.parser import StructuredParser
from .schema.fingerprint import fingerprint_schema
from .schema.instructions import schema_instructions
from .schema.introspection import SchemaInfo, SchemaTarget
from .schema.named import NamedSchemas, NamedSchemaTargets
from .schema.options import SchemaOptions

__all__ = ["XStructuredMiddleware"]

type _Handler = Callable[[ModelRequest[Any]], ModelResponse[Any]]
type _AsyncHandler = Callable[
    [ModelRequest[Any]], Awaitable[ModelResponse[Any]]
]


class XStructuredMiddleware(AgentMiddleware[AgentState[Any], Any, Any]):
    """Validate an agent's final answer against a Pydantic schema.

    Every model call gets the schema instructions in its system message. When
    the model answers without tool calls, the answer is parsed and validated,
    and the agent state's ``structured_response`` is set to an
    `XStructuredResult`. Tool-calling turns pass through unchanged, so the
    agent keeps using its tools.

    Set ``config["configurable"]["xstructured_context"]`` on the agent call to
    pass a Pydantic validation context.

    Args:
        schema: A schema target, a `SchemaInfo`, or named schemas.
        envelope: Envelope delimiters. Defaults to ``<xstructured>`` / ``</xstructured>``.
        parser_config: Limits and recovery settings. An envelope is always required.
        multiple: Expect a JSON array of values.
        multiple_envelopes: Expect one named envelope per applicable named schema.
        inject_instructions: Add the instructions to every model call. Disable it
            to place `instructions` in the agent's own system prompt.
        repair_config: Ask the agent's model to correct an invalid final answer,
            within these bounds. Disabled when omitted.
        schema_options: Pydantic configuration and JSON Schema generation options.
        renderer: An `InstructionRenderer` for the instructions.
        extractor: An `OutputTextExtractor` for the final AI message.
        recovery: A `RecoveryStrategy` choosing the substrings tried as JSON.
        decoder: A `JsonDecoder` for each candidate.
        repair_prompt: A `RepairPromptBuilder`; a string prompt becomes a human
            message, and messages are appended as they are.
        observer: An `Observer` receiving one observation per final answer.
        name: The middleware name. Defaults to the class name.

    Raises:
        ValueError: If *repair_prompt* is given without *repair_config*.
        TypeError: If an extension point does not subclass its base class.
        SchemaError: If the schema is invalid.

    Example:
        ```python
        import asyncio

        from langchain.agents import create_agent
        from pydantic import BaseModel
        from xstructured.agents import XStructuredMiddleware
        from xstructured.testing import ScriptedChatModel


        class Report(BaseModel):
            severity: str
            summary: str


        model = ScriptedChatModel.of(
            "Database failover. <xstructured>"
            '{"severity": "high", "summary": "Primary database failed over"}'
            "</xstructured>"
        )
        agent = create_agent(model, middleware=[XStructuredMiddleware(Report)])


        async def main() -> None:
            state = await agent.ainvoke(
                {"messages": [("human", "Summarize the incident.")]}
            )
            report = state["structured_response"].structured
            assert report.severity == "high"


        asyncio.run(main())
        ```
    """

    def __init__(
        self,
        schema: SchemaTarget | SchemaInfo | NamedSchemaTargets | NamedSchemas,
        *,
        envelope: EnvelopeSpec | None = None,
        parser_config: ParserConfig | None = None,
        multiple: bool = False,
        multiple_envelopes: bool = False,
        inject_instructions: bool = True,
        repair_config: RepairConfig | None = None,
        schema_options: SchemaOptions | None = None,
        renderer: InstructionRenderer | None = None,
        extractor: OutputTextExtractor | None = None,
        recovery: RecoveryStrategy | None = None,
        decoder: JsonDecoder | None = None,
        repair_prompt: RepairPromptBuilder | None = None,
        observer: Observer | None = None,
        name: str | None = None,
    ) -> None:
        super().__init__()
        if repair_prompt is not None and repair_config is None:
            raise ValueError("repair_prompt requires repair_config")
        envelope = envelope or EnvelopeSpec()
        config = parser_config or ParserConfig()
        if not config.require_envelope:
            config = config.model_copy(update={"require_envelope": True})
        self._parser: StructuredParser[Any] = StructuredParser(
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
        self._inject_instructions = inject_instructions
        self._repair_config = repair_config or RepairConfig(enabled=False)
        self._repair_prompt = (
            DefaultRepairPrompt()
            if repair_prompt is None
            else require_instance(
                repair_prompt, RepairPromptBuilder, "repair_prompt"
            )
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
        self._name = name or type(self).__name__
        self._settings = _Settings(
            parser=self._parser,
            extractor=self._extractor,
            repair_config=self._repair_config,
            repair_prompt=self._repair_prompt,
            instructions=self._instructions,
            fingerprint=self._fingerprint,
        )
        self._attributes: Mapping[str, AttributeValue] = {
            "xstructured.name": self._name,
            "xstructured.schema_fingerprint": self._fingerprint,
            "xstructured.multiple": multiple,
            "xstructured.multiple_envelopes": multiple_envelopes,
        }

    def __repr__(self) -> str:
        return f"XStructuredMiddleware(name={self._name!r})"

    @property
    @override
    def name(self) -> str:
        """The middleware name."""
        return self._name

    @property
    def parser(self) -> StructuredParser[Any]:
        """The parser used for every final answer."""
        return self._parser

    @property
    def instructions(self) -> str:
        """The instructions added to every model call."""
        return self._instructions

    @property
    def schema_fingerprint(self) -> str:
        """SHA-256 fingerprint of the schema (see `fingerprint_schema`)."""
        return self._fingerprint

    @override
    async def awrap_model_call(
        self, request: ModelRequest[Any], handler: _AsyncHandler
    ) -> ModelResponse[Any]:
        request = self._inject(request)
        response = await handler(request)
        if (message := _final_message(response)) is None:
            return response
        observation = self._observe()
        try:
            answer = _Answer(self._settings, request, response, message)
            while (repair := answer.repair_request()) is not None:
                answer.receive(await handler(repair))
            result = answer.result()
        except BaseException as exc:
            observation.fail(exc)
            raise
        observation.succeed(result_attributes(result))
        return ModelResponse(
            result=answer.response.result, structured_response=result
        )

    @override
    def wrap_model_call(
        self, request: ModelRequest[Any], handler: _Handler
    ) -> ModelResponse[Any]:
        request = self._inject(request)
        response = handler(request)
        if (message := _final_message(response)) is None:
            return response
        observation = self._observe()
        try:
            answer = _Answer(self._settings, request, response, message)
            while (repair := answer.repair_request()) is not None:
                answer.receive(handler(repair))
            result = answer.result()
        except BaseException as exc:
            observation.fail(exc)
            raise
        observation.succeed(result_attributes(result))
        return ModelResponse(
            result=answer.response.result, structured_response=result
        )

    def _observe(self) -> Observation:
        return observe(self._observer, "agent", self._attributes)

    def _inject(self, request: ModelRequest[Any]) -> ModelRequest[Any]:
        if not self._inject_instructions:
            return request
        system = request.system_message
        merged = with_system_instructions(
            [] if system is None else [system], self._instructions
        )
        return request.override(system_message=cast("SystemMessage", merged[0]))


@dataclass(frozen=True, slots=True)
class _Settings:
    parser: StructuredParser[Any]
    extractor: OutputTextExtractor
    repair_config: RepairConfig
    repair_prompt: RepairPromptBuilder
    instructions: str
    fingerprint: str


class _Answer:
    """Parse one final answer, asking the model for corrections within the budget."""

    def __init__(
        self,
        settings: _Settings,
        request: ModelRequest[Any],
        response: ModelResponse[Any],
        message: AIMessage,
    ) -> None:
        self._settings = settings
        self._request = request
        self._context = validation_context(ensure_config())
        self._started = perf_counter()
        self._failures: list[str] = []
        self._attempt = 0
        self._parsed: ParseResult[Any] | None = None
        self._error: ParseError | None = None
        self.response = response
        self._message = message
        self._original = self._text = settings.extractor.text(message)
        try:
            self._parsed = self._parse()
        except ParseError as error:
            config = settings.repair_config
            if not config.enabled or isinstance(error, LimitExceededError):
                raise
            self._error = error

    def repair_request(self) -> ModelRequest[Any] | None:
        """Return the next repair request, or ``None`` once the answer is valid.

        Raises:
            RepairError: If the attempt budget is spent.
        """
        if self._parsed is not None:
            return None
        settings = self._settings
        attempts = settings.repair_config.max_attempts
        if self._attempt >= attempts:
            raise exhausted_error(
                self._original, self._failures, attempts
            ) from self._error
        self._attempt += 1
        prompt = settings.repair_prompt.build(
            text=self._text,
            error=cast("ParseError", self._error),
            attempt=self._attempt,
            max_attempts=attempts,
            instructions=settings.instructions,
        )
        return self._request.override(
            messages=cast(
                "list[AnyMessage]",
                [
                    *self._request.messages,
                    self._message,
                    *_prompt_messages(prompt),
                ],
            )
        )

    def receive(self, response: ModelResponse[Any]) -> None:
        """Parse the model's reply to a repair request."""
        message = _final_message(response)
        if message is None:
            self._fail(
                ParseError(
                    f"Repair attempt {self._attempt} called tools instead of answering",
                    text=self._text,
                )
            )
            return
        self.response, self._message = response, message
        self._text = self._settings.extractor.text(message)
        try:
            parsed = self._parse()
        except ParseError as error:
            self._fail(error)
            return
        self._parsed = replace(
            parsed, repaired=True, repair_attempts=self._attempt
        )

    def result(self) -> XStructuredResult[Any]:
        """The validated result; call it once `repair_request` returns ``None``."""
        parsed = cast("ParseResult[Any]", self._parsed)
        return build_result(
            fingerprint=self._settings.fingerprint,
            raw=self._message,
            raw_text=self._text,
            content=remove_spans(self._text, parsed.envelope_spans),
            parsed=parsed,
            envelope_count=len(parsed.envelope_spans),
            parse_duration=perf_counter() - self._started,
        )

    def _parse(self) -> ParseResult[Any]:
        return self._settings.parser.parse(self._text, context=self._context)

    def _fail(self, error: ParseError) -> None:
        self._failures.append(str(error))
        self._error = error


def _final_message(response: ModelResponse[Any]) -> AIMessage | None:
    for message in reversed(response.result):
        if isinstance(message, AIMessage):
            return None if message.tool_calls else message
    return None


def _prompt_messages(prompt: Any) -> list[BaseMessage]:
    if isinstance(prompt, str):
        return [HumanMessage(prompt)]
    if isinstance(prompt, BaseMessage):
        return [prompt]
    if isinstance(prompt, Sequence) and all(
        isinstance(message, BaseMessage) for message in prompt
    ):
        return list(prompt)
    raise TypeError(
        "repair_prompt must build a string, a message, or a sequence of messages, "
        f"not {type(prompt).__name__}"
    )
