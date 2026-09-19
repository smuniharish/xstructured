# Streaming UI events

[`examples/streaming_ui_events.py`](https://github.com/xstructured/xstructured/blob/main/examples/streaming_ui_events.py)
shows how to forward ordered xstructured events to a terminal, browser SSE
adapter, or websocket. Text remains incremental while the structured payload
is separately delimited:

```python
from xstructured import StreamEventKind, with_xstructured_output

for event in with_xstructured_output(model, StatusUpdate).stream(messages):
    if event.kind is StreamEventKind.TEXT_DELTA:
        ui.append_text(event.text or "")
    elif event.kind is StreamEventKind.STRUCTURED_DELTA:
        ui.append_json_delta(event.text or "")
    elif event.kind is StreamEventKind.RESULT:
        ui.finish(event.result.structured)
```

`sequence` is monotonic, so an event adapter can preserve ordering even when
the transport batches messages.

## Live run output

The following output was captured from a live provider run. This response
contained no natural-language text deltas, so the first event was the
structured lifecycle event. Chunk counts and boundaries vary by provider:

```text
=== Streaming UI events ===
[event=structured_start sequence=0]
[event=structured_delta sequence=1] ... [event=structured_delta sequence=24]
[event=structured_end sequence=25]
[event=result sequence=26]
structured=StatusUpdate(status='Unknown', next_step='Check the deployment logs or provide the deployment details to determine the current status.')
```
