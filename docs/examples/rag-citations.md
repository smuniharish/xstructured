# RAG with citations

The final step of a retrieval-augmented pipeline: the model answers from retrieved
documents and must cite them. The schema requires at least one citation, and the script
verifies that each quote appears verbatim in the cited document.

```python title="examples/rag_citations.py"
--8<-- "examples/rag_citations.py"
```

## Output

=== "Live"

    ```text
    === RAG answer with citations (live: gpt-5.6-luna) ===
    Answer: Before a production rollout, an approved change record is required. Deploys also use canary traffic for ten minutes before the full rollout.
    [policy-4] Production changes require an approved change record. (verified: True)
    [runbook-17] Deploys use canary traffic for ten minutes before full rollout. (verified: True)
    ```

=== "Offline"

    ```text
    === RAG answer with citations (offline: scripted model) ===
    Answer: You need an approved change record, and the deploy must run on canary traffic for ten minutes before full rollout.
    [policy-4] Production changes require an approved change record. (verified: True)
    [runbook-17] Deploys use canary traffic for ten minutes before full rollout. (verified: True)
    ```

Schema validation guarantees the *shape* of the citations; checks such as "the quote
exists in the source" belong in your application, as shown here.
