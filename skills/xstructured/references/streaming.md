# Streaming

`wrapper.stream(input)` and `wrapper.astream(input)` yield ordered `StreamEvent` values:

| `event.kind` | Meaning | Field |
| --- | --- | --- |
| `TEXT_DELTA` | Prose outside the envelope | `event.text` |
| `STRUCTURED_START` | The opening delimiter arrived | |
| `STRUCTURED_DELTA` | Raw payload text | `event.text` |
| `STRUCTURED_END` | The payload validated | `event.structured` |
| `RESULT` | The stream ended; emitted once | `event.result` (`XStructuredResult`) |

`event.sequence` numbers are contiguous from 0.

```python
from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from xstructured import StreamEventKind, with_xstructured_output


class Status(BaseModel):
    status: str
    next_step: str


wrapper = with_xstructured_output(init_chat_model("openai:gpt-5-mini"), Status)
for event in wrapper.stream("How did the deploy go?"):
    if event.kind is StreamEventKind.TEXT_DELTA:
        print(event.text, end="")
    elif event.kind is StreamEventKind.STRUCTURED_END:
        print("\ncard:", event.structured)
```

## Rules

- Call `stream()` on the wrapper itself to get events. Inside a composed chain
  (`wrapper | step`), the wrapper emits only its final `XStructuredResult`.
- Streaming needs a complete envelope; a missing or unclosed one raises `ParseError` at the
  end of the stream.
- Repair does not run while streaming events. Use `invoke`, or a composed chain, when
  repair is required.
- `multiple_envelopes=True` cannot be streamed with `stream()`.

## Other sources of text

`StreamDecoder` applies the protocol to any chunk source:

```python
from xstructured import StreamDecoder, StructuredParser

decoder = StreamDecoder(StructuredParser(Status))
events = []
chunks = [
    '<xstructured>{"status": "ok", ',
    '"next_step": "none"}</xstructured>',
]
for chunk in chunks:
    events.extend(decoder.feed(chunk))
decoder.finalize()
assert decoder.result.value == Status(status="ok", next_step="none")
```
