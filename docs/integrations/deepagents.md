# Deep Agents (optional)

[`deepagents`](https://github.com/langchain-ai/deepagents) is an optional,
example-only dependency (in the `examples` dependency group) -- it is never
imported by the `xstructured` package itself.

`create_deep_agent` produces the same kind of `{"messages": [...]}`
dict-based `Runnable` as `create_agent`, so it is wrapped with the exact
same `RunnableLambda` adapter pattern described in
[the LangChain integration guide](langchain.md#wrapping-a-create_agent-agent):

```python
from deepagents import create_deep_agent
from langchain_core.runnables import RunnableLambda
from xstructured import with_xstructured_output

deep_agent = create_deep_agent(model="openai:gpt-4o-mini", tools=[])


def run_deep_agent(messages):
    state = deep_agent.invoke({"messages": list(messages)})
    return state["messages"][-1]


extractor = with_xstructured_output(RunnableLambda(run_deep_agent), ContactInfo)
```

See [`examples/deep_agent_optional.py`](https://github.com/xstructured/xstructured/blob/main/examples/deep_agent_optional.py)
for the full, runnable script -- it is gated on both an API key being set
*and* `deepagents` being importable, and prints a clear skip message when
either is unavailable (for example, in CI, where it is exercised as a
smoke test with no API key set).
