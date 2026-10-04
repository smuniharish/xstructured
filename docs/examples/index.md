# Examples

Nine runnable scripts in [`examples/`](https://github.com/smuniharish/xstructured/tree/master/examples)
show `xstructured` in realistic applications. Every script runs in two modes:

- **Offline** (default): a scripted chat model replays a realistic response, so the script
  runs anywhere without credentials. The test suite runs every example this way and checks
  its output.
- **Live**: with `EXPLABS_API_KEY` set, the scripts call the
  [Experiential Labs](https://api.experientiallabs.ai) OpenAI-compatible API.

| Variable | Default | Purpose |
| --- | --- | --- |
| `EXPLABS_API_KEY` | — | Enables live mode. |
| `EXPLABS_MODEL` | `gpt-5.6-luna` | Model name. |
| `EXPLABS_BASE_URL` | `https://api.experientiallabs.ai/v1` | API endpoint. |

## Run them

=== "bash"

    ```bash
    uv sync  # also installs the example dependencies

    # Offline: a scripted chat model replays a realistic response.
    uv run python examples/single_agent_extraction.py

    # Live: calls the Experiential Labs API.
    EXPLABS_API_KEY="your-key" uv run python examples/single_agent_extraction.py
    ```

=== "PowerShell"

    ```powershell
    uv sync  # also installs the example dependencies

    # Offline: a scripted chat model replays a realistic response.
    uv run python examples/single_agent_extraction.py

    # Live: calls the Experiential Labs API.
    $env:EXPLABS_API_KEY = "your-key"
    uv run python examples/single_agent_extraction.py
    ```

Keep API keys in your environment or a secrets manager; never commit them.

## Gallery

| Example | Shows |
| --- | --- |
| [Single-agent extraction](single-agent-extraction.md) | A `create_agent` agent wrapped through a message adapter. |
| [Multi-agent pipeline](multi-agent-pipeline.md) | Two agents with validated hand-offs. |
| [Deep Agents research](deep-agent.md) | A `create_deep_agent` planning agent with a validated summary. |
| [LangGraph workflow](langgraph-workflow.md) | Routing a graph on a validated `Literal` field. |
| [RAG with citations](rag-citations.md) | Answers that must cite and quote retrieved documents. |
| [Incident analysis](incident-analysis.md) | Prose explanation plus a typed action plan. |
| [Streaming UI events](streaming-ui-events.md) | Ordered text and structured events for a UI. |
| [Multiple payloads and repair](multiple-payloads-repair.md) | A typed list of mixed schemas, with bounded repair. |
| [Named envelopes](named-envelopes.md) | Separate envelopes for separate schemas in one reply. |

Live outputs on these pages were captured from real runs against `gpt-5.6-luna`; wording
varies between runs, while the structure is always validated.
