# Quickstart

## Wrap a chat model

Any Runnable whose output is a string or a LangChain message can be wrapped. The wrapper
adds the schema instructions to the input and validates the response.

```python
from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from xstructured import with_xstructured_output


class Contact(BaseModel):
    name: str
    email: str
    company: str | None = None


model = init_chat_model("openai:gpt-5-mini")
extractor = with_xstructured_output(model, Contact)
result = extractor.invoke(
    "Please loop in Priya Shah (priya.shah@example.com) from Acme Corp "
    "on the review."
)

print(result.structured)  # Contact(name='Priya Shah', ...)
print(result.content)  # The model's natural-language reply, envelope removed.
print(result.raw)  # The original AIMessage.
```

The input can be a string, a `PromptValue`, or a list of messages (including tuples such
as `("human", "...")`). Message inputs get the instructions as a system message.

## Wrap a chain

Wrap the whole chain so the instructions reach the model and its output is validated. A
chain that starts with a prompt template takes a dictionary, which the wrapper cannot add
instructions to, so put them in the prompt yourself and disable injection:

```python
from langchain_core.prompts import ChatPromptTemplate

from xstructured import EnvelopeSpec, schema_instructions

instructions = schema_instructions(Contact, envelope=EnvelopeSpec())
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You extract contact details.\n\n{instructions}"),
        ("human", "{message}"),
    ]
).partial(instructions=instructions)

chain = with_xstructured_output(
    prompt | init_chat_model("openai:gpt-5-mini"),
    Contact,
    inject_instructions=False,
)
result = chain.invoke({"message": "Reach Priya at priya.shah@example.com."})
```

!!! tip
    If you leave injection on and pass an input that cannot carry instructions, such as a
    dictionary, the wrapper raises a `TypeError` before calling the model, so a missing
    instruction never turns into a confusing parsing failure.

## Wrap an agent

`create_agent` graphs exchange `{"messages": [...]}` state. Adapt the graph to a
message-in, message-out Runnable at its boundary:

```python
from langchain.agents import create_agent
from langchain_core.runnables import RunnableLambda

agent = create_agent(model="openai:gpt-5-mini", tools=[])


def run_agent(messages):
    return agent.invoke({"messages": list(messages)})["messages"][-1]


extractor = with_xstructured_output(RunnableLambda(run_agent), Contact)
```

See [Agents and Deep Agents](../integrations/agents.md) for details.

## Stream text and data

```python
from xstructured import StreamEventKind

message = "Add Priya Shah (priya.shah@example.com) to the review."
for event in extractor.stream(message):
    if event.kind is StreamEventKind.TEXT_DELTA:
        print(event.text, end="")
    elif event.kind is StreamEventKind.STRUCTURED_END:
        print("\nValidated:", event.structured)
```

## Parse text you already have

Without LangChain, `StructuredParser` validates text from any source:

```python
from xstructured import StructuredParser

parser = StructuredParser(Contact)
reply = (
    "Sure!\n"
    "```json\n"
    '{"name": "Priya Shah", "email": "priya.shah@example.com"}\n'
    "```"
)
result = parser.parse(reply)

print(result.value)  # Contact(name='Priya Shah', ..., company=None)
print(result.recovered)  # True: the JSON was found inside a Markdown fence.
```

Next, read the [user guide](../guide/index.md) or browse the [examples](../examples/index.md).
