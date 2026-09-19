# RAG answer with citations

[`examples/rag_citations.py`](https://github.com/xstructured/xstructured/blob/main/examples/rag_citations.py)
shows the final, provider-independent part of a RAG pipeline: retrieved
documents are included in a prompt and the answer must contain citations.

```python
class Citation(BaseModel):
    source_id: str
    quote: str

class CitedAnswer(BaseModel):
    answer: str
    citations: list[Citation] = Field(min_length=1)

result = with_xstructured_output(model, CitedAnswer).invoke(
    [HumanMessage(content=f"Use only these documents:\n{context}\n\nQuestion: {question}")]
)
for citation in result.structured.citations:
    print(citation.source_id, citation.quote)
```

Use your retriever in place of the small in-memory `DOCUMENTS` mapping in the
complete example. The schema prevents a successful response from silently
omitting evidence.

## Live run output

The following output was captured from a live provider run. Each citation is
still validated as a typed `Citation` value:

```text
=== RAG answer with citations ===
Answer: A production rollout requires an approved change record and a ten-minute canary period.
[policy-4] Production changes require an approved change record.
[runbook-17] Deploys use canary traffic for ten minutes before full rollout.
```
