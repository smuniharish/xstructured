# Deep Agents research

`create_deep_agent` builds a planning agent with sub-agents and a virtual filesystem on
top of LangGraph. It exchanges the same `{"messages": [...]}` state as `create_agent`, so
the same adapter validates its final summary.

```python title="examples/deep_agent.py"
--8<-- "examples/deep_agent.py"
```

## Output

=== "Live"

    ```text
    === Deep agent research summary (live: gpt-5.6-luna) ===
    Topic: Retrieval-augmented generation (RAG)
    - RAG combines a language model with an external retrieval system that finds relevant documents or data for each query.
    - The retrieved information is included in the model's prompt, helping generate answers that are more current, specific, and grounded in source material.
    - RAG can reduce unsupported statements and avoid retraining the model for every knowledge update, but its quality depends on retrieval accuracy and source reliability.
    Open questions: []
    ```

=== "Offline"

    ```text
    === Deep agent research summary (offline: scripted model) ===
    Topic: Retrieval-augmented generation
    - RAG grounds model answers in retrieved documents instead of retraining.
    - Answer quality depends mostly on retrieval quality, chunking, and reranking.
    - Evaluation needs both retrieval metrics and answer faithfulness checks.
    Open questions: ['How should conflicting sources be resolved?']
    ```

`key_points` is bounded with `Field(min_length=1, max_length=5)`, so a summary with no
points, or a rambling one, is rejected.
