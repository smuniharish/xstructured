# LangGraph workflow

A triage node validates the model's decision into a `Triage` value stored in graph state,
and a conditional edge routes on its `priority` field: critical requests page the on-call
engineer, everything else opens a ticket.

```python title="examples/langgraph_workflow.py"
--8<-- "examples/langgraph_workflow.py"
```

## Output

=== "Live"

    ```text
    === LangGraph incident triage (live: gpt-5.6-luna) ===
    Triage: Triage(priority='critical', team='Payments Engineering', summary='Checkout is failing for every customer in the EU, indicating a widespread regional payment outage requiring immediate investigation and mitigation.')
    Action: Paged the Payments Engineering on-call engineer
    ```

=== "Offline"

    ```text
    === LangGraph incident triage (offline: scripted model) ===
    Triage: Triage(priority='critical', team='payments', summary='Checkout fails for every customer in the EU.')
    Action: Paged the payments on-call engineer
    ```

Because `priority` is a `Literal`, the router never sees an unexpected value such as
`"urgent"`: the response would fail validation first.
