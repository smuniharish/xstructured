# Examples

Runnable scripts that demonstrate `xstructured` wrapping real LangChain v1
agents. Each script:

- checks for the environment variable(s) and optional packages it needs,
  and exits cleanly with an explanation instead of failing when they are
  missing, so the suite is safe to run (or smoke-test) anywhere;
- otherwise makes a real, live call to an LLM provider.

| Script | Demonstrates | Requires |
| --- | --- | --- |
| [`single_agent_extraction.py`](single_agent_extraction.py) | Wrapping one `create_agent` agent with `with_xstructured_output` | `EXPLABS_API_KEY` |
| [`multi_agent_pipeline.py`](multi_agent_pipeline.py) | An extractor agent feeding a reviewer agent, each independently schema-validated | `EXPLABS_API_KEY` |
| [`deep_agent_optional.py`](deep_agent_optional.py) | The same wrapping pattern applied to an optional `deepagents` deep agent | `deepagents` installed, `EXPLABS_API_KEY` |
| [`langgraph_workflow.py`](langgraph_workflow.py) | A current `StateGraph` workflow with a validated triage node | `EXPLABS_API_KEY` |
| [`rag_citations.py`](rag_citations.py) | A retrieval-style prompt producing validated answer citations | `EXPLABS_API_KEY` |
| [`incident_analysis.py`](incident_analysis.py) | An operator report turned into a structured incident action plan | `EXPLABS_API_KEY` |
| [`streaming_ui_events.py`](streaming_ui_events.py) | Ordered text and structured events suitable for a UI or SSE adapter | `EXPLABS_API_KEY` |
| [`multiple_payloads_repair.py`](multiple_payloads_repair.py) | Heterogeneous array payloads with bounded LLM-assisted repair | `EXPLABS_API_KEY` |
| [`named_envelopes.py`](named_envelopes.py) | Separate named envelopes mapped to separate Pydantic schemas | `EXPLABS_API_KEY` |

## Running the examples

```bash
uv sync --group examples
$env:EXPLABS_API_KEY = "..."     # PowerShell; use `export` on bash/zsh
# Optional overrides:
$env:EXPLABS_MODEL = "gpt-5.6-luna"
$env:EXPLABS_BASE_URL = "https://api.experientiallabs.ai/v1"

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

Without `EXPLABS_API_KEY` set, every script prints a short explanation and
exits with status `0`. [`tests/test_examples_smoke.py`](../tests/test_examples_smoke.py)
runs them in exactly that credential-free mode as part of the regular test
suite, so the examples stay importable and in sync with the public API
without ever requiring network access or API keys in CI.

## Live validation checklist

The examples are designed for an operator-controlled live run. Configure the
provider locally, then run every script and retain the terminal output for the
release record:

```powershell
uv sync --group examples
$env:EXPLABS_API_KEY = "<set locally; never commit or paste into docs>"
$env:EXPLABS_MODEL = "gpt-5.6-luna"
$env:EXPLABS_BASE_URL = "https://api.experientiallabs.ai/v1"

uv run python examples/single_agent_extraction.py
uv run python examples/multi_agent_pipeline.py
uv run python examples/deep_agent_optional.py
uv run python examples/langgraph_workflow.py
uv run python examples/rag_citations.py
uv run python examples/incident_analysis.py
uv run python examples/streaming_ui_events.py
uv run python examples/multiple_payloads_repair.py
uv run python examples/named_envelopes.py
```

Model wording, generated values, repair activation, and streaming chunk
boundaries vary. A live run validates provider compatibility; the deterministic
test suite remains the source of truth for parser and protocol correctness.

## Why wrap the agent instead of using `create_agent(output_schema=...)`?

`create_agent`'s built-in `output_schema` is a good default. `xstructured`
is for the cases it does not cover: composing structured extraction with
*any* `Runnable` (not only `create_agent`), streaming ordered text and
structured deltas to a UI as they arrive, and a schema-fingerprinted,
envelope-based protocol that tolerates markdown fences and conversational
prose around the JSON payload. See
[the LangChain integration guide](../docs/integrations/langchain.md) for the
full comparison.
