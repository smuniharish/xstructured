"""Extension points.

Every customizable behavior is an abstract base class with a default
implementation. To change a behavior, subclass the base class, implement its
abstract methods, and pass an instance to `StructuredParser`,
`with_xstructured_output`, or `XStructuredMiddleware`. Constructors reject any
object that does not subclass the matching base class.

| Base class | Default | Controls |
| --- | --- | --- |
| `InstructionRenderer` | `DefaultInstructionRenderer` | Instructions sent to the model |
| `InstructionInjector` | `MessageInstructionInjector` | Where instructions go in the input |
| `OutputTextExtractor` | `MessageTextExtractor` | How output and chunk text is read |
| `RecoveryStrategy` | `ConservativeRecovery` | Which substrings of a response are tried |
| `JsonDecoder` | `StrictJsonDecoder` | How a candidate is decoded |
| `RepairPromptBuilder` | `DefaultRepairPrompt` | The input sent to the repair Runnable |
| `Observer` | none; `OpenTelemetryObserver` (``otel`` extra) | Telemetry for every call |

The extension points are synchronous on purpose: they transform text in memory
and never perform I/O, so they run directly on the event loop of the async
APIs without blocking it.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .core.errors import ParseError
    from .envelope.spec import EnvelopeSpec
    from .schema.introspection import SchemaInfo
    from .schema.named import NamedSchemas

__all__ = [
    "AttributeValue",
    "InstructionInjector",
    "InstructionRenderer",
    "JsonDecoder",
    "Observation",
    "Observer",
    "OutputTextExtractor",
    "RecoveryStrategy",
    "RepairPromptBuilder",
]

type AttributeValue = str | bool | int | float
"""A telemetry attribute value, compatible with OpenTelemetry span attributes."""


class InstructionRenderer(ABC):
    """Base class for renderers of the instructions sent to the model.

    `DefaultInstructionRenderer` renders deterministic English instructions
    followed by the JSON Schema. Subclass it to change the wording, or this
    class to render instructions from scratch.
    """

    @abstractmethod
    def render(
        self,
        schema: SchemaInfo | NamedSchemas | Mapping[str, Any],
        *,
        envelope: EnvelopeSpec | None,
        multiple: bool,
        multiple_envelopes: bool,
    ) -> str:
        """Return instructions for *schema*.

        Args:
            schema: The resolved schema, named schemas, or a JSON Schema document.
            envelope: The envelope the model must use, or ``None`` when the model
                must respond with JSON only.
            multiple: Ask for a JSON array of values.
            multiple_envelopes: Ask for one named envelope per applicable schema.
        """


class InstructionInjector(ABC):
    """Base class for adding instructions to the wrapped Runnable's input."""

    @abstractmethod
    def inject(self, value: Any, instructions: str) -> Any:
        """Return a copy of *value* that carries *instructions*.

        Raises:
            TypeError: If *value* cannot carry instructions.
        """


class OutputTextExtractor(ABC):
    """Base class for reading response text from the wrapped Runnable's output."""

    @abstractmethod
    def text(self, output: Any) -> str:
        """Return the text of one complete output.

        Raises:
            TypeError: If *output* has no text.
        """

    def chunk_text(self, chunk: Any) -> str:
        """Return the text of one streamed chunk. Defaults to `text`.

        Return ``""`` for chunks that carry no response text, such as tool
        messages in a LangGraph ``messages`` stream.
        """
        return self.text(chunk)


class RecoveryStrategy(ABC):
    """Base class for strategies that choose which substrings of a response to parse.

    The parser tries candidates in the order they are yielded, stopping at the
    first one that decodes and validates, and never tries more than
    `RecoveryConfig.max_candidates`. The first candidate should be the text as
    given; a strategy must not rewrite JSON syntax.
    """

    @abstractmethod
    def candidates(self, text: str) -> Iterable[str]:
        """Yield candidate substrings of *text* in the order to try them."""


class JsonDecoder(ABC):
    """Base class for JSON decoders applied to each recovery candidate.

    The decoded value selects the item and name in array and named-schema
    modes; validation always runs on `json_text` in Pydantic's JSON mode, so
    strict models keep accepting JSON representations such as ISO dates.
    """

    @abstractmethod
    def decode(self, text: str, *, max_nesting_depth: int) -> Any:
        """Decode *text*.

        Raises:
            ValueError: If *text* is not acceptable JSON. Every other exception
                propagates unchanged.
        """

    def json_text(self, text: str, value: Any) -> str:
        """Return the standard JSON text to validate for a decoded candidate.

        Defaults to serializing *value*. Override it to return *text* unchanged
        when the decoder only accepts standard JSON.
        """
        del text
        return json.dumps(value, ensure_ascii=False)


class RepairPromptBuilder(ABC):
    """Base class for building the input sent to the repair Runnable."""

    @abstractmethod
    def build(
        self,
        *,
        text: str,
        error: ParseError,
        attempt: int,
        max_attempts: int,
        instructions: str,
    ) -> Any:
        """Return the repair Runnable's input for one attempt.

        Args:
            text: The response to correct.
            error: Why the response failed.
            attempt: The attempt number, starting at 1.
            max_attempts: The configured attempt budget.
            instructions: The instructions the response had to follow.
        """


class Observation(ABC):
    """One observed call, finished exactly once with `succeed` or `fail`."""

    @abstractmethod
    def succeed(self, attributes: Mapping[str, AttributeValue]) -> None:
        """Record a successful call with result *attributes*."""

    @abstractmethod
    def fail(self, error: BaseException) -> None:
        """Record a failed or cancelled call."""


class Observer(ABC):
    """Base class for telemetry backends.

    An observer receives one `Observation` per wrapper call. Attributes never
    contain model output, only sizes, counts, flags, and names, so telemetry
    does not leak prompts or responses.
    """

    @abstractmethod
    def start(
        self, operation: str, attributes: Mapping[str, AttributeValue]
    ) -> Observation:
        """Begin observing *operation* (for example ``"invoke"`` or ``"stream"``)."""


def require_instance[C](value: object, base: type[C], argument: str) -> C:
    """Return *value* when it is an instance of *base*.

    Raises:
        TypeError: If *value* does not subclass *base*.
    """
    if not isinstance(value, base):
        raise TypeError(
            f"{argument} must be an instance of {base.__name__}, not "
            f"{type(value).__name__}"
        )
    return value
