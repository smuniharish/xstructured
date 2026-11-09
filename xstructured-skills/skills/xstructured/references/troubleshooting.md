# Troubleshooting

All xstructured errors derive from `XStructuredError`. Output problems derive
from `ParseError`, which keeps the model output in `error.text`, never in the
message, so the message is safe to log.

## Construction errors

| Message | Cause | Fix |
| --- | --- | --- |
| `SchemaError: Cannot introspect schema target ...` | The schema is not something Pydantic can validate. | Pass a model class, a `TypeAdapter`, or an annotation such as `list[Item]`. |
| `SchemaError: Invalid schema name ...` | A named-schema key has other characters. | Use 1 to 64 letters, digits, `_`, `.`, or `-`. |
| `EnvelopeError: Envelope delimiters must differ` / `must not contain double quotes or backslashes` | A custom `EnvelopeSpec` is invalid. | Use delimiters such as `<result>` and `</result>`. |
| `ValueError: repair_config and repair_prompt require a repair Runnable` | The wrapper got a repair option without `repair=`. | Pass `repair=model`, or drop the option. |
| `ValueError: repair_prompt requires repair_config` | The middleware got `repair_prompt` alone. | Add `repair_config=RepairConfig(...)`. |
| `TypeError: decoder must be an instance of JsonDecoder, not ...` | An extension point does not subclass its base class. | Subclass the ABC; see the `xstructured-extend` skill. |

## Call errors

| Message | Cause | Fix |
| --- | --- | --- |
| `TypeError: Cannot add xstructured instructions to input of type dict...` | A prompt-template input (a plain dict) reached the wrapper with injection on. | Use `XStructuredOutputParser` at the end of the chain, or `inject_instructions=False` with `wrapper.instructions` in the template. |
| `TypeError: The wrapped Runnable must return str, BaseMessage, or a state mapping with a 'messages' key, not ...` | The Runnable returns something else. | Return a message, or pass `extractor=` an `OutputTextExtractor` subclass. |
| `TypeError: The output's 'messages' contain no AI message` | The graph returned a state without an AI reply. | Check the graph's last node; set `MessageTextExtractor(messages_key=...)` if the key differs. |
| `ParseError: No complete <xstructured>...</xstructured> envelope was found` | The model ignored or never received the instructions. | Check `wrapper.instructions` reaches the model, keep `inject_instructions=True`, or add bounded repair. |
| `RecoveryError: No recovery candidate is valid JSON matching the schema (N tried): ...` | The JSON is invalid or fails validation; `error.failures` lists one reason per candidate. | Read the failure, describe fields with `Field(description=...)`, or add repair. Do not loosen the schema. |
| `LimitExceededError: ... exceeds the configured limit of N characters` | The response is larger than a limit; `error.limit` names it. | Investigate; raise the limit only for legitimate sizes. |
| `RepairError: LLM-assisted repair did not produce a valid response in N attempt(s)` | Every repair failed; `error.__cause__` is the last failure. | Improve instructions or use a stronger model. Do not raise `max_attempts` past a small number. |
| `ValueError: Named envelopes cannot be streamed` | `astream()` with `multiple_envelopes=True`. | Use `ainvoke`, or stream inside a composed chain. |

## Unexpected results

- **`result.content` is empty**: the model replied with only the envelope.
  Ask for a short explanation in your prompt if prose is needed.
- **`result.recovered` is `True`**: the JSON came from a fence or prose.
  Usually fine; `RecoveryConfig(enabled=False)` demands exact JSON.
- **A validator does not see the context**: pass it under `CONTEXT_KEY` in
  `config["configurable"]`, or set `SchemaOptions(context=...)`.
- **No `structured_response` in agent state**: the middleware is missing from
  `middleware=[...]`, or the agent ended on a tool call.
- **Instructions appear twice**: the prompt also asks for JSON. Remove the
  hand-written request, or set `inject_instructions=False`.

## Handling pattern

```python
import logging

from xstructured import LimitExceededError, ParseError

log = logging.getLogger(__name__)


async def extract(wrapper, text: str):
    try:
        return (await wrapper.ainvoke(text)).structured
    except LimitExceededError as error:
        log.warning("response too large: %s", error.limit)
        return None
    except ParseError as error:
        log.warning("invalid model output: %s", error)  # never error.text
        return None
```

To resample instead of repairing, use
`wrapper.with_retry(retry_if_exception_type=(ParseError,), stop_after_attempt=2)`;
to try another model, `wrapper.with_fallbacks([other_wrapper])`.
