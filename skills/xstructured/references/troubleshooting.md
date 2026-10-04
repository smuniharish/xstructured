# Troubleshooting

All errors derive from `XStructuredError`; output problems derive from `ParseError`, which
keeps the model output in `error.text` (never in the message).

| Error or symptom | Likely cause | Fix |
| --- | --- | --- |
| `TypeError: Cannot add xstructured instructions to input of type dict` | A prompt-template chain or agent state was passed with injection on. | Pass `inject_instructions=False` and put the instructions in the prompt, or adapt the input to messages. |
| `TypeError: The wrapped Runnable must return str or BaseMessage values` | The wrapped Runnable returns a dict, such as agent state. | Adapt it with a `RunnableLambda` that returns `state["messages"][-1]`. |
| `ParseError: No complete <xstructured>...</xstructured> envelope was found` | The model ignored the instructions or did not receive them. | Check the instructions reach the model (`wrapper.instructions`), strengthen the prompt, or add bounded repair. |
| `RecoveryError` | JSON invalid or not matching the schema. `error.failures` lists each candidate. | Read the schema failure, clarify field descriptions, or constrain the prompt; consider repair. |
| `LimitExceededError` (`error.limit`, `error.maximum`) | The response exceeded a configured limit. | Investigate the response; raise the limit only if legitimate responses are larger. |
| `RepairError` (`error.attempts`, `error.failures`) | Repair attempts all failed. | Inspect `error.__cause__`, improve instructions, or fall back to another model. |
| `ValueError: Named envelopes cannot be streamed` | `stream()` with `multiple_envelopes=True`. | Use `invoke`, or stream inside a composed chain. |
| `SchemaError` at construction | The schema is not a Pydantic-compatible target, or a named schema name is invalid. | Use a model class, `TypeAdapter`, or annotation; names are 1-64 of `A-Za-z0-9_.-`. |
| `EnvelopeError` at construction | Delimiters contain `"` or `\`, are equal, or are not tag-style for named envelopes. | Use delimiters such as `<result>` / `</result>`. |
| Empty `result.content` | The model replied with only the envelope. | Ask for a short explanation in the prompt if prose is needed. |
| `result.recovered` is `True` | JSON came from a fence or surrounding prose. | Usually fine; to require exact JSON, disable recovery. |

## Handling pattern

```python
from xstructured import LimitExceededError, ParseError, StructuredParser


def safe_parse(parser: StructuredParser[dict], text: str) -> dict | None:
    try:
        return parser.parse(text).value
    except LimitExceededError:
        return None  # Too large: do not retry or send elsewhere.
    except ParseError as error:
        # Never log error.text if it may hold PII.
        print(f"invalid model output: {error}")
        return None
```

## Retrying the model

`wrapper.with_retry(retry_if_exception_type=(RecoveryError,), stop_after_attempt=2)`
resamples the model; `wrapper.with_fallbacks([other_wrapper])` tries another model.
