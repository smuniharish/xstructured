# Integration guide

Use the verified integration patterns from the repository instead of inventing a
custom wrapper:

- [LangChain integration](https://xstructured.readthedocs.io/en/latest/integrations/langchain/)
- [Project README](https://github.com/smuniharish/xstructured/blob/master/README.md)
- [Single-agent extraction example](https://github.com/smuniharish/xstructured/blob/master/examples/single_agent_extraction.py)
- [Multi-agent pipeline example](https://github.com/smuniharish/xstructured/blob/master/examples/multi_agent_pipeline.py)

## Wrap a chat model

Any `Runnable` that returns a `str` or a `BaseMessage` can be wrapped directly:

```python
from langchain.chat_models import init_chat_model
from xstructured import with_xstructured_output

model = init_chat_model("openai:gpt-4o-mini")
extractor = with_xstructured_output(model, ContactInfo)
result = extractor.invoke("Reach Priya Shah at priya.shah@example.com.")
```

## Wrap a create_agent graph

`create_agent` emits `{"messages": [...]}` state, not a bare string or message,
so the adapter narrows the state to its final message before wrapping:

```python
from langchain.agents import create_agent
from langchain_core.runnables import RunnableLambda
from xstructured import with_xstructured_output

agent = create_agent(model="openai:gpt-4o-mini", tools=[])


def run_agent(messages):
    state = agent.invoke({"messages": list(messages)})
    return state["messages"][-1]

extractor = with_xstructured_output(RunnableLambda(run_agent), ContactInfo)
```

## Use native features when they already fit

`create_agent(..., output_schema=SomeModel)` is already the right default when
it matches the response contract. `xstructured` is the adapter when the app needs
one boundary for a runnable, streaming events, or a cross-provider output
contract without changing the rest of the graph.

## Keep the boundaries narrow

Do not modify the underlying model, agent, or graph orchestration just to add
xstructured. Prefer a thin adapter at the boundary and keep validation inside
the wrapper.
