# Extension points

Every customizable behavior is an abstract base class (ABC) with a default.
Subclass it, implement the abstract methods, and pass an instance to the
keyword in the table. Constructors reject anything that does not subclass the
matching base class with `TypeError: <keyword> must be an instance of <Base>`.

| Base class | Default | Keyword | Accepted by | Contract |
| --- | --- | --- | --- | --- |
| `InstructionRenderer` | `DefaultInstructionRenderer` | `renderer=` | wrapper, middleware, output parser, `schema_instructions` | none |
| `InstructionInjector` | `MessageInstructionInjector` | `injector=` | wrapper | `InstructionInjectorContract` |
| `OutputTextExtractor` | `MessageTextExtractor` | `extractor=` | wrapper, middleware | `OutputTextExtractorContract` |
| `RecoveryStrategy` | `ConservativeRecovery` | `recovery=` | all, `StructuredParser` | `RecoveryStrategyContract` |
| `JsonDecoder` | `StrictJsonDecoder` | `decoder=` | all, `StructuredParser` | `JsonDecoderContract` |
| `RepairPromptBuilder` | `DefaultRepairPrompt` | `repair_prompt=` | wrapper, middleware | none |
| `Observer` | none; `OpenTelemetryObserver` | `observer=` | wrapper, middleware | `ObserverContract` |

The extension points are synchronous on purpose: they transform text in
memory and run directly on the event loop of the async APIs. Never do
blocking I/O in them; an observer buffers and flushes in the background.

## Signatures and promises

`JsonDecoder`

- `decode(text, *, max_nesting_depth) -> Any`: raise `ValueError` (or a
  subclass) for text you do not accept, so the parser tries the next
  candidate; anything else propagates and fails the call. Enforce
  `max_nesting_depth`. Delegating to `StrictJsonDecoder` first and re-raising
  its `JsonSafetyError` keeps the safety rules.
- `json_text(text, value) -> str`: standard JSON for the decoded value;
  Pydantic validates it in JSON mode. The default serializes `value`;
  override it to return `text` when you accept only standard JSON.

`RecoveryStrategy`

- `candidates(text) -> Iterable[str]`: the stripped text first, then
  non-empty, distinct substrings of the text, in the order to try. Never
  rewrite JSON (no quote fixing, no comma removal). The parser stops at the
  first valid candidate and at `RecoveryConfig.max_candidates`.

`Observer` and `Observation`

- `start(operation, attributes) -> Observation`: one new observation per
  call. `operation` is `"invoke"`, `"stream"`, `"transform"`, or `"agent"`.
- `Observation.succeed(attributes)` or `Observation.fail(error)`: exactly one
  of them is called once. `fail` also receives cancellations
  (`asyncio.CancelledError`, `GeneratorExit`). See [observers.md](observers.md).

`InstructionInjector`

- `inject(value, instructions) -> Any`: return a new value carrying the
  instructions; never modify the input; raise `TypeError` for inputs that
  cannot carry them.

`OutputTextExtractor`

- `text(output) -> str`: the response text of a complete output; raise
  `TypeError` when there is none.
- `chunk_text(chunk) -> str`: the text of one streamed chunk, `""` for chunks
  without response text. Defaults to `text`.
- `MessageTextExtractor(messages_key=..., nodes=...)` already handles other
  state keys and filtering a LangGraph `messages` stream by node; prefer
  configuring it over subclassing.

`InstructionRenderer`

- `render(schema, *, envelope, multiple, multiple_envelopes) -> str`.
  Subclass `DefaultInstructionRenderer` to change wording while keeping the
  schema and envelope description. Changing instructions changes what models
  produce; re-run the project's live evaluations.

`RepairPromptBuilder`

- `build(*, text, error, attempt, max_attempts, instructions) -> Any`: the
  repair Runnable's input for one attempt. Include `instructions` and `error`
  so the model can correct itself. Do not include secrets; `text` is the
  model's own output.

## Contract tests

```python
from xstructured.testing import (
    InstructionInjectorContract,
    OutputTextExtractorContract,
)


class TestMyInjector(InstructionInjectorContract):
    def make_injector(self):
        return MyInjector()

    def make_input(self):
        return {"question": "What is 2 + 2?"}


class TestMyExtractor(OutputTextExtractorContract):
    def make_extractor(self):
        return MyExtractor()

    def make_output(self, text):
        return {"answer": text}
```

Each contract class contributes one plain test method per promise; pytest
collects them, and so does unittest when the class also inherits
`unittest.TestCase`. `RecoveryStrategyContract.sample_texts()` can be
overridden to add responses your strategy targets. For a decoder, a strategy,
or an observer, `scripts/check_extension.py MODULE:FACTORY` runs the same
contract without pytest.

## Downstream customization

Customization of the libraries xstructured builds on stays available:

- Pydantic: `schema_options=SchemaOptions(...)` (strict, extra, context,
  aliases, `ConfigDict`, JSON Schema generator and mode).
- LangChain: every `Runnable` option (`with_config`, callbacks, tags,
  `with_retry`, `with_fallbacks`) and any chat model.
- LangChain agents: the middleware composes with other `AgentMiddleware`.
- OpenTelemetry: `OpenTelemetryObserver(tracer_provider=...)`.
