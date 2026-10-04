<!-- docs-test: run -->

# Observability

## Result metadata

Every `XStructuredResult` carries read-only `metadata`:

| Key | When present | Meaning |
| --- | --- | --- |
| `schema_fingerprint` | always | SHA-256 [fingerprint](schemas.md#fingerprints) of the schema. |
| `envelope_count` | always | Envelopes in the response that produced the value. |
| `parse_duration` | always | Seconds spent extracting and validating (including repair). |
| `message_id` | message outputs | The message `id`. |
| `response_metadata` | message outputs | The provider's response metadata. |
| `usage_metadata` | when reported | Token usage, merged across streamed chunks. |

The result fields `recovered`, `repaired`, `repair_attempts`, and `schema_name` describe
how the value was obtained.

```python
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

from xstructured import fingerprint_schema, with_xstructured_output


class Answer(BaseModel):
    value: int


message = AIMessage(
    content='Forty-two. <xstructured>{"value": 42}</xstructured>',
    id="msg-1",
    usage_metadata={"input_tokens": 20, "output_tokens": 9, "total_tokens": 29},
)
wrapper = with_xstructured_output(RunnableLambda(lambda _: message), Answer)
result = wrapper.invoke("q")

assert result.metadata["schema_fingerprint"] == fingerprint_schema(Answer)
assert result.metadata["envelope_count"] == 1
assert result.metadata["usage_metadata"]["total_tokens"] == 29
```

## Tracing

The wrapper is a traced LangChain run. With LangSmith or any callback handler, each call
appears as one `XStructuredRunnable` run (or the name you give with
`.with_config(run_name=...)`), with the wrapped Runnable as a child run. Repair calls are
child runs tagged `xstructured:repair`.

```python
from langchain_core.callbacks import BaseCallbackHandler


class Recorder(BaseCallbackHandler):
    def __init__(self) -> None:
        self.runs = []

    def on_chain_start(
        self, serialized, inputs, *, run_id, parent_run_id=None, **kwargs
    ):
        self.runs.append((kwargs.get("name"), parent_run_id is None))


def answer(_: str) -> AIMessage:
    return message


recorder = Recorder()
with_xstructured_output(RunnableLambda(answer), Answer).invoke(
    "q", config={"callbacks": [recorder], "run_name": "extract_answer"}
)

assert recorder.runs == [("extract_answer", True), ("answer", False)]
```

`astream_events()` includes the wrapper's protocol events as `on_chain_stream` events and
the model's tokens as `on_chat_model_stream` events, so one event stream can drive a UI.
