# Integration patterns

## Chat model

```python
from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from xstructured import with_xstructured_output


class Summary(BaseModel):
    title: str
    bullets: list[str]


model = init_chat_model("openai:gpt-5-mini")
summarizer = with_xstructured_output(model, Summary)
result = summarizer.invoke("Summarize the release notes.")
```

String inputs get the instructions appended; message lists get them in a system message.

## Chain with a prompt template

A prompt template takes a dict, which cannot carry injected instructions. Put the
instructions in the prompt and disable injection:

```python
from langchain_core.prompts import ChatPromptTemplate

from xstructured import EnvelopeSpec, schema_instructions

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You summarize documents.\n\n{instructions}"),
        ("human", "{document}"),
    ]
).partial(instructions=schema_instructions(Summary, envelope=EnvelopeSpec()))

chain = with_xstructured_output(
    prompt | init_chat_model("openai:gpt-5-mini"),
    Summary,
    inject_instructions=False,
)
result = chain.invoke({"document": "..."})
```

## create_agent and Deep Agents

Agent graphs exchange `{"messages": [...]}` state. Adapt them at the boundary:

```python
from collections.abc import Sequence

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableLambda

agent = create_agent(model="openai:gpt-5-mini", tools=[])


def run_agent(messages: Sequence[BaseMessage]) -> BaseMessage:
    return agent.invoke({"messages": list(messages)})["messages"][-1]


typed_agent = with_xstructured_output(RunnableLambda(run_agent), Summary)
result = typed_agent.invoke([HumanMessage("Summarize the incident.")])
```

The same adapter works for `deepagents.create_deep_agent`. With a checkpointer, prefer
`inject_instructions=False` and put `typed_agent.instructions` in the agent's
`system_prompt`, so instructions are not appended to the stored history on every call.

## LangGraph node

Call the wrapper inside a node and store `result.structured` in state; route with
conditional edges on typed fields such as a `Literal` priority.

## Composition

The wrapper is a normal Runnable:

- `wrapper.with_retry(...)`, `wrapper.with_fallbacks([...])`, `wrapper.with_config(...)`;
- `wrapper.batch([...])` and `await wrapper.abatch([...])`;
- `wrapper | next_step`: the next step receives the `XStructuredResult`, whether the chain
  is invoked or streamed.

Each call is one traced run with the wrapped Runnable as a child run.

## Multiple values in one response

| Need | Option | `structured` |
| --- | --- | --- |
| A list of one type | `multiple=True` | `list[T]` |
| One of several types | `{"name": Schema, ...}` | the matched type; `schema_name` says which |
| A list of mixed types | named schemas + `multiple=True` | list of mixed types |
| Prose with one envelope per type | named schemas + `multiple_envelopes=True` | `dict[name, value]` |
