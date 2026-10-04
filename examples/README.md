# Examples

Runnable scripts that show xstructured in realistic applications. Each one runs **offline**
by default, replaying a realistic response from a scripted chat model, or **live** against
the Experiential Labs OpenAI-compatible API when `EXPLABS_API_KEY` is set.

```bash
uv sync  # also installs the example dependencies

# Offline: a scripted chat model replays a realistic response.
uv run python examples/single_agent_extraction.py

# Live: calls the Experiential Labs API.
EXPLABS_API_KEY="your-key" uv run python examples/single_agent_extraction.py
```

`EXPLABS_MODEL` (default `gpt-5.6-luna`) and `EXPLABS_BASE_URL` (default
`https://api.experientiallabs.ai/v1`) override the model and endpoint. Keep keys in your
environment; never commit them.

| Script | Shows |
| --- | --- |
| [`single_agent_extraction.py`](single_agent_extraction.py) | A `create_agent` agent wrapped through a message adapter. |
| [`multi_agent_pipeline.py`](multi_agent_pipeline.py) | Two agents with validated hand-offs. |
| [`deep_agent.py`](deep_agent.py) | A Deep Agents planning agent with a validated summary. |
| [`langgraph_workflow.py`](langgraph_workflow.py) | Routing a LangGraph workflow on a validated field. |
| [`rag_citations.py`](rag_citations.py) | Answers that must cite retrieved documents. |
| [`incident_analysis.py`](incident_analysis.py) | Prose explanation plus a typed action plan. |
| [`streaming_ui_events.py`](streaming_ui_events.py) | Ordered text and structured events for a UI. |
| [`multiple_payloads_repair.py`](multiple_payloads_repair.py) | A typed list of mixed schemas with bounded repair. |
| [`named_envelopes.py`](named_envelopes.py) | Separate envelopes for separate schemas. |

The test suite runs every script offline and checks its output (`tests/test_examples.py`);
`uv run pytest -m live` runs them against the live API. Walkthroughs with captured output
are in the [documentation](https://xstructured.readthedocs.io/en/latest/examples/).
