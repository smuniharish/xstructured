# Single-agent extraction

A `create_agent` agent extracts a contact from a message. The agent graph exchanges
`{"messages": [...]}` state, so a `RunnableLambda` adapts it to message-in, message-out;
`with_xstructured_output` wraps the adapter and validates the agent's final answer.

```python title="examples/single_agent_extraction.py"
--8<-- "examples/single_agent_extraction.py"
```

## Output

=== "Live"

    ```text
    === Single-agent extraction (live: gpt-5.6-luna) ===
    Reply:      'Priya Shah <priya.shah@example.com> from Acme Corp.'
    Structured: ContactInfo(name='Priya Shah', email='priya.shah@example.com', company='Acme Corp')
    Recovered:  False
    ```

=== "Offline"

    ```text
    === Single-agent extraction (offline: scripted model) ===
    Reply:      'I found one contact in your message.'
    Structured: ContactInfo(name='Priya Shah', email='priya.shah@example.com', company='Acme Corp')
    Recovered:  False
    ```

`Reply` is the agent's prose with the envelope removed; `Structured` is the validated
model. See [Agents and Deep Agents](../integrations/agents.md) for the adapter pattern.
