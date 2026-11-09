# Streaming

`wrapper.astream(input)` yields ordered `StreamEvent` values while the model
is still generating:

| `event.kind` | Meaning | Field |
| --- | --- | --- |
| `TEXT_DELTA` | Prose outside the envelope | `event.text` |
| `STRUCTURED_START` | The opening delimiter arrived | |
| `STRUCTURED_DELTA` | Raw payload text | `event.text` |
| `STRUCTURED_END` | The payload validated | `event.structured` |
| `RESULT` | The stream ended; emitted exactly once | `event.result` |

`event.sequence` numbers are contiguous from 0. The `TEXT_DELTA` texts join
into `result.content`.

```python
from pydantic import BaseModel

from xstructured import StreamEventKind, with_xstructured_output


class Status(BaseModel):
    status: str
    next_step: str


async def render(model, question: str) -> Status:
    wrapper = with_xstructured_output(model, Status)
    async for event in wrapper.astream(question):
        if event.kind is StreamEventKind.TEXT_DELTA:
            print(event.text, end="", flush=True)
        elif event.kind is StreamEventKind.STRUCTURED_END:
            print("\ncard:", event.structured)
        elif event.kind is StreamEventKind.RESULT:
            return event.result.structured
    raise AssertionError("a stream always ends with RESULT")
```

The final result equals what `ainvoke` returns, with message chunks merged
into one `AIMessage` and usage metadata summed.

## Rules

- Call `astream()` on the wrapper itself to get events. Inside a composed
  chain (`wrapper | step`), the wrapper consumes the stream and passes only the
  final `XStructuredResult` on, so repair works there as with `ainvoke`.
- Streaming needs a complete envelope; a missing or unclosed one raises
  `ParseError` at the end of the stream.
- Repair does not run while streaming events, because events were already
  delivered.
- `multiple_envelopes=True` cannot be streamed with `astream()`.
- An agent streams through LangGraph: use the agent's own `astream()` and read
  `structured_response` from the final state.
- `astream_events()` carries both the model's token events and the wrapper's
  protocol events (`on_chain_stream`).
- Breaking out of the loop, or cancelling the task, closes the underlying
  model stream and reports the call as cancelled to observers.

## Other sources of text

`StreamDecoder` applies the protocol to chunks from anywhere, such as a
provider SDK or a WebSocket:

```python
from xstructured import EnvelopeSpec, StreamDecoder, StructuredParser

decoder = StreamDecoder(StructuredParser(Status, envelope=EnvelopeSpec()))
events = []
for chunk in [
    "All good. <xstruc",
    'tured>{"status": "ok", ',
    '"next_step": "none"}</xstructured>',
]:
    events.extend(decoder.feed(chunk))
decoder.finalize()
assert decoder.result.value == Status(status="ok", next_step="none")
assert decoder.text == "All good. "
```

`finalize()` raises `ParseError` when no complete envelope arrived. The
decoder enforces the parser's size limits as chunks arrive.
