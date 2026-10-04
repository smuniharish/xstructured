# Streaming UI events

Stream ordered events the way a terminal, server-sent events endpoint, or WebSocket
handler would consume them: print text as it arrives, and render the status card as soon
as the structured payload validates.

```python title="examples/streaming_ui_events.py"
--8<-- "examples/streaming_ui_events.py"
```

## Output

=== "Live"

    ```text
    === Streaming UI events (live: gpt-5.6-luna) ===
    Deployment 2026.10.04-1 completed successfully at 14:02 UTC, with all 12 health checks passing in eu-west and us-east and error rates at baseline.

    [card ready after 14 structured deltas] StatusUpdate(status='Deployment completed successfully; all health checks pass and error rates are at baseline.', next_step='Continue monitoring eu-west and us-east.')

    [result #50] recovered=False
    ```

=== "Offline"

    ```text
    === Streaming UI events (offline: scripted model) ===
    The deployment finished and all health checks are green.
    [card ready after 15 structured deltas] StatusUpdate(status='healthy', next_step='Promote the release to all regions.')
     I will keep monitoring for the next hour.
    [result #50] recovered=False
    ```

Event `sequence` numbers are contiguous, so a client can detect gaps or reorder messages
that a transport delivers out of order. See [Streaming](../guide/streaming.md).
