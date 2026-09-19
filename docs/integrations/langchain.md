# LangChain

`xstructured.langchain` provides `with_xstructured_output` and
`XStructuredRunnable`, the only parts of the library that depend on
`langchain-core`.

## Wrapping a chat model

Any `Runnable` that returns a `str` or a `BaseMessage` can be wrapped
directly:

```python
from langchain.chat_models import init_chat_model
from xstructured import with_xstructured_output

model = init_chat_model("openai:gpt-4o-mini")
extractor = with_xstructured_output(model, ContactInfo)
result = extractor.invoke("Reach Priya Shah at priya.shah@example.com.")
```

## Wrapping a `create_agent` agent

`create_agent`'s compiled graph takes and returns a `{"messages": [...]}`
dict, not a bare `str`/`BaseMessage`/message sequence, so it needs a small
`RunnableLambda` adapter before it can be wrapped:

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

See [`examples/single_agent_extraction.py`](https://github.com/xstructured/xstructured/blob/main/examples/single_agent_extraction.py)
and [`examples/multi_agent_pipeline.py`](https://github.com/xstructured/xstructured/blob/main/examples/multi_agent_pipeline.py)
for complete, runnable versions of this pattern, including a two-agent
pipeline where each agent is wrapped and validated independently.

## Why wrap instead of `output_schema`?

`create_agent(..., output_schema=SomeModel)` already exists and is the
right default when it applies. `xstructured` is for the situations that
do not cover: plain `Runnable`s with no agent-level schema hook,
already-built agents/chains you cannot or do not want to reconstruct,
incremental streaming of structured output, and providers where native
structured-output support is unavailable or undesirable.

See [Why xstructured?](why-xstructured.md) for ten concrete application
scenarios and guidance on when LangChain or LangGraph native features are the
better choice.

## Instruction injection

`XStructuredRunnable` automatically injects a system message built from
`schema_instructions` for `str`, `PromptValue`, or `Sequence[BaseMessage]`
inputs (pass `inject_instructions=False` to `with_xstructured_output` to
disable this). It does **not** inspect or modify dict-shaped input (such as
`create_agent`'s native `{"messages": [...]}` state) -- this is exactly why
the `RunnableLambda` adapter above narrows the input to a message sequence
first.

## Streaming

```python
for event in extractor.stream([HumanMessage(content="...")]):
    match event.kind:
        case StreamEventKind.TEXT_DELTA:
            print(event.text, end="")
        case StreamEventKind.RESULT:
            print(event.result.structured)
```

See [Streaming](../concepts/streaming.md) for the full event-ordering
contract.
