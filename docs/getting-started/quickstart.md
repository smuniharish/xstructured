# Quickstart

```python
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda
from langchain.agents import create_agent
from pydantic import BaseModel

from xstructured import with_xstructured_output


class ContactInfo(BaseModel):
    name: str
    email: str


agent = create_agent(model="openai:gpt-4o-mini", tools=[])


def run_agent(messages):
    # create_agent's compiled graph takes/returns a {"messages": [...]} state,
    # so it is adapted to the plain-message Runnable contract xstructured expects.
    state = agent.invoke({"messages": list(messages)})
    return state["messages"][-1]


extractor = with_xstructured_output(RunnableLambda(run_agent), ContactInfo)

result = extractor.invoke(
    [HumanMessage(content="Reach Priya Shah at priya.shah@example.com.")]
)

print(result.structured)  # ContactInfo(name='Priya Shah', email='priya.shah@example.com')
print(result.content)     # the agent's natural-language reply, envelope stripped
print(result.raw)         # the original AIMessage
```

See [`examples/single_agent_extraction.py`](https://github.com/xstructured/xstructured/blob/main/examples/single_agent_extraction.py)
for a runnable version of this snippet, and
[the LangChain integration guide](../integrations/langchain.md) for the full
`invoke`/`ainvoke`/`batch`/`abatch`/`stream`/`astream` contract.

## Without an agent

`with_xstructured_output` composes with *any* `Runnable` that returns a
string or a `BaseMessage` -- including a bare chat model:

```python
from langchain.chat_models import init_chat_model
from xstructured import with_xstructured_output

model = init_chat_model("openai:gpt-4o-mini")
extractor = with_xstructured_output(model, ContactInfo)
result = extractor.invoke("Reach Priya Shah at priya.shah@example.com.")
```

## Parsing text you already have

If you already have model output as text (for example from a provider SDK
you are calling directly), use `StructuredParser` without the `Runnable`
wrapper:

```python
from xstructured import StructuredParser

result = StructuredParser(ContactInfo).parse(model_output_text)
print(result.value)  # ContactInfo(...)
```
