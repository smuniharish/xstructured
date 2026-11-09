# Single-agent extraction

A `create_agent` agent with a contact-lookup tool extracts a contact from a
message. `XStructuredMiddleware` adds the format instructions to the agent's
system prompt and validates the final answer into
`state["structured_response"]`, while the agent keeps calling tools normally.

```python title="examples/single_agent_extraction.py"
--8<-- "examples/single_agent_extraction.py"
```

## Output

```text
=== Single-agent extraction (offline: scripted model) ===
Reply:      'I found one contact in your message.'
Structured: ContactInfo(name='Priya Shah', email='priya.shah@example.com', company='Acme Corp')
Tool calls: 1
```

`Reply` is the agent's prose with the envelope removed; `Structured` is the
validated model. See [Agents and Deep Agents](../integrations/agents.md) for
the middleware.
