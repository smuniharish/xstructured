<!-- docs-test: run -->

# Extension points

Every customizable behavior of xstructured is an abstract base class with a
default implementation. Subclass the base class, implement its abstract
methods, and pass an instance to the entry point. Constructors reject any
object that does not subclass the matching base class, with a `TypeError` that
names the argument.

| Base class | Default | Controls | Accepted by |
| --- | --- | --- | --- |
| `InstructionRenderer` | `DefaultInstructionRenderer` | The instructions sent to the model | all entry points, `schema_instructions` |
| `InstructionInjector` | `MessageInstructionInjector` | Where instructions go in the input | `with_xstructured_output` |
| `OutputTextExtractor` | `MessageTextExtractor` | How output and chunk text is read | `with_xstructured_output`, `XStructuredMiddleware` |
| `RecoveryStrategy` | `ConservativeRecovery` | Which substrings of a response are tried | all entry points, `StructuredParser` |
| `JsonDecoder` | `StrictJsonDecoder` | How a candidate is decoded | all entry points, `StructuredParser` |
| `RepairPromptBuilder` | `DefaultRepairPrompt` | The input sent for repair | `with_xstructured_output`, `XStructuredMiddleware` |
| `Observer` | none | Telemetry for every call | `with_xstructured_output`, `XStructuredMiddleware` |

The extension points are synchronous on purpose: they transform text in memory
and never perform I/O, so they run directly on the event loop of the async
APIs without blocking it. `xstructured.testing` has a
[contract test suite](testing.md#contract-tests) for each of them.

## Instructions

Subclass `DefaultInstructionRenderer` to add to the default wording, or
`InstructionRenderer` to write instructions from scratch.

```python
import asyncio
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from xstructured import (
    DefaultInstructionRenderer,
    EnvelopeSpec,
    NamedSchemas,
    SchemaInfo,
    StructuredParser,
    with_xstructured_output,
)
from xstructured.testing import ScriptedChatModel


class Ticket(BaseModel):
    queue: str
    urgent: bool


class HouseStyle(DefaultInstructionRenderer):
    def render(
        self,
        schema: SchemaInfo | NamedSchemas | Mapping[str, Any],
        *,
        envelope: EnvelopeSpec | None,
        multiple: bool,
        multiple_envelopes: bool,
    ) -> str:
        base = super().render(
            schema,
            envelope=envelope,
            multiple=multiple,
            multiple_envelopes=multiple_envelopes,
        )
        return f"{base}\n\nAnswer in British English."


model = ScriptedChatModel.of(
    'Routed. <xstructured>{"queue": "billing", "urgent": false}</xstructured>'
)
router = with_xstructured_output(model, Ticket, renderer=HouseStyle())
assert router.instructions.endswith("British English.")
result = asyncio.run(router.ainvoke("I was charged twice."))
assert result.structured == Ticket(queue="billing", urgent=False)
```

## Recovery and decoding

A `RecoveryStrategy` yields the substrings of a response to try, starting with
the text as given; a `JsonDecoder` decodes each one. Validation always runs on
standard JSON in Pydantic's JSON mode. This decoder accepts the single-quoted
keys and values some models produce:

```python
import ast
import json

from xstructured import (
    ConservativeRecovery,
    JsonDecoder,
    JsonSafetyError,
    RecoveryStrategy,
    StrictJsonDecoder,
)


class PythonLiteralDecoder(JsonDecoder):
    def decode(self, text: str, *, max_nesting_depth: int) -> Any:
        try:
            return StrictJsonDecoder().decode(
                text, max_nesting_depth=max_nesting_depth
            )
        except JsonSafetyError:
            raise  # Too deep, duplicate keys, NaN: never fall back.
        except ValueError:
            try:
                value = ast.literal_eval(text)
                json.dumps(value, allow_nan=False)
            except (SyntaxError, TypeError, ValueError) as error:
                raise ValueError(str(error)) from error
            return value


class LastLineFirst(RecoveryStrategy):
    def candidates(self, text: str) -> list[str]:
        stripped = text.strip()
        last = stripped.splitlines()[-1].strip() if stripped else ""
        found = [stripped, last, *ConservativeRecovery().candidates(text)]
        return [item for item in dict.fromkeys(found) if item]


lenient = StructuredParser(
    Ticket, decoder=PythonLiteralDecoder(), recovery=LastLineFirst()
)
parsed = lenient.parse("Routing now.\n{'queue': 'billing', 'urgent': True}")
assert parsed.value == Ticket(queue="billing", urgent=True)
assert json.loads(parsed.json_text) == {"queue": "billing", "urgent": True}
```

A decoder raises `ValueError` for text it does not accept, so the parser moves
on to the next candidate; any other exception propagates. A recovery strategy
yields the stripped text first and only ever yields substrings of it. Check
both with their [contract suites](testing.md#contract-tests).

## Inputs and outputs

An `InstructionInjector` decides how instructions are added to the wrapped
Runnable's input; the default handles strings, prompt values, message lists,
and `{"messages": [...]}` states, and raises `TypeError` for anything else. An `OutputTextExtractor`
reads the response text from outputs and stream chunks; the default reads
strings, messages, and `{"messages": [...]}` states. This pair lets a Runnable
that takes and returns dictionaries be wrapped:

```python
from langchain_core.runnables import RunnableLambda

from xstructured import InstructionInjector, OutputTextExtractor


class QuestionInjector(InstructionInjector):
    def inject(self, value: Any, instructions: str) -> Any:
        if not isinstance(value, dict):
            raise TypeError("expected a dict input")
        return {**value, "question": f"{value['question']}\n{instructions}"}


class AnswerExtractor(OutputTextExtractor):
    def text(self, output: Any) -> str:
        if not isinstance(output, dict) or "answer" not in output:
            raise TypeError("expected a dict with an answer")
        return output["answer"]


def service(payload: dict[str, str]) -> dict[str, str]:
    assert "<xstructured>" in payload["question"]
    return {
        "answer": 'Done. <xstructured>{"queue": "sales", "urgent": true}'
        "</xstructured>"
    }


wrapped = with_xstructured_output(
    RunnableLambda(service),
    Ticket,
    injector=QuestionInjector(),
    extractor=AnswerExtractor(),
)
answer = asyncio.run(wrapped.ainvoke({"question": "Buy 500 seats?"}))
assert answer.structured.queue == "sales"
```

## Repair prompts

A `RepairPromptBuilder` builds the input for each repair attempt from the
failed text, the error, the attempt number, and the instructions. Return a
string, a message, or a list of messages. See [Bounded repair](repair.md).

```python
from xstructured import ParseError, RepairPromptBuilder


class TerseRepair(RepairPromptBuilder):
    def build(
        self,
        *,
        text: str,
        error: ParseError,
        attempt: int,
        max_attempts: int,
        instructions: str,
    ) -> str:
        return (
            f"Attempt {attempt}/{max_attempts}. Fix: {error}\n"
            f"{instructions}\n\nResponse:\n{text}"
        )
```

## Telemetry

An `Observer` receives one observation per call; see
[Observability](observability.md#observers) and
[OpenTelemetry](../integrations/opentelemetry.md).

## Pydantic options

Pydantic's own options (strict mode, extra fields, validation context, aliases,
JSON Schema generation) are not extension points: they pass straight through
with [`SchemaOptions`](configuration.md#pydantic-options).
