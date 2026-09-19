# Examples

Runnable, env-gated scripts under [`examples/`](https://github.com/xstructured/xstructured/tree/main/examples)
demonstrate `xstructured` wrapping real LangChain v1 agents. Each script
checks for the environment variable(s) and optional packages it needs and
exits cleanly with an explanation when they are missing, so the whole suite
is safe to run -- or smoke-test, as
[`tests/test_examples_smoke.py`](https://github.com/xstructured/xstructured/blob/main/tests/test_examples_smoke.py)
does in CI -- with no API keys or network access at all.

| Script | Demonstrates |
| --- | --- |
| [Single-agent extraction](single-agent-extraction.md) | Wrapping one `create_agent` agent with `with_xstructured_output` |
| [Multi-agent pipeline](multi-agent-pipeline.md) | An extractor agent feeding a reviewer agent, each independently schema-validated |
| [Deep agents (optional)](deep-agents.md) | The same wrapping pattern applied to an optional `deepagents` deep agent |
| [LangGraph workflow](langgraph-workflow.md) | A `StateGraph` workflow with a validated triage node |
| [RAG with citations](rag-citations.md) | A retrieval-style answer with validated source citations |
| [Incident analysis](incident-analysis.md) | A structured incident summary and action plan |
| [Streaming UI events](streaming-ui-events.md) | Ordered text and structured events for a UI or SSE adapter |
| [Multiple payloads and repair](multiple-payloads-repair.md) | A real provider model returning heterogeneous payloads with bounded repair |
| [Named envelopes](named-envelopes.md) | Separate named envelopes mapped to separate Pydantic schemas |

## Capability coverage

The examples intentionally cover the meaningful combinations supported by the
public API rather than duplicating every Cartesian-product permutation:

| Capability | Example |
| --- | --- |
| One schema, natural language plus structured value | Single-agent extraction |
| Named heterogeneous schemas in one response | Multiple payloads and repair; Named envelopes |
| Multiple validated values in one envelope | Multiple payloads and repair |
| Opt-in LLM-assisted repair and repair metadata | Multiple payloads and repair |
| Independent schemas across cooperating agents | Multi-agent pipeline |
| LangGraph state orchestration | LangGraph workflow |
| Deep-agent adapter | Deep Agents |
| Retrieval context and typed citations | RAG with citations |
| Operational severity and action-plan fields | Incident analysis |
| Incremental text, structured deltas, and final result | Streaming UI events |
| Provider-independent Runnable composition | Single-agent extraction and LangGraph workflow |

Async invocation, batching, conservative recovery, resource limits, custom
envelopes, and repair retry bounds are covered by the offline integration and
property tests. They are not repeated as extra network examples because the
provider transport does not change those contracts.

## Running the examples

```bash
uv sync --group examples
export EXPLABS_API_KEY="..."
export EXPLABS_MODEL="gpt-5.6-luna"
export EXPLABS_BASE_URL="https://api.experientiallabs.ai/v1"

uv run python examples/single_agent_extraction.py
uv run python examples/multi_agent_pipeline.py
uv run python examples/deep_agent_optional.py   # requires deepagents too
uv run python examples/langgraph_workflow.py
uv run python examples/rag_citations.py
uv run python examples/incident_analysis.py
uv run python examples/streaming_ui_events.py
uv run python examples/multiple_payloads_repair.py
uv run python examples/named_envelopes.py
```
