# Quickstart

xstructured attaches to LangChain in three ways. All of them return an
[`XStructuredResult`](../api/results.md): the model's prose in `content` and
the validated Pydantic value in `structured`.

| You have | Use |
| --- | --- |
| A chat model, chain, or graph | `with_xstructured_output(runnable, Schema)` |
| An agent from `create_agent` or `create_deep_agent` | `XStructuredMiddleware(Schema)` |
| A `prompt | model` chain you build yourself | `XStructuredOutputParser(Schema)` |

## Wrap a chat model

```python
import asyncio

from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from xstructured import with_xstructured_output


class Contact(BaseModel):
    name: str
    email: str
    company: str | None = None


async def main() -> None:
    model = init_chat_model("openai:gpt-5-mini")
    extractor = with_xstructured_output(model, Contact)
    result = await extractor.ainvoke(
        "Please loop in Priya Shah (priya.shah@example.com) from Acme Corp "
        "on the review."
    )
    print(result.structured)  # Contact(name='Priya Shah', ...)
    print(result.content)  # The model's reply, envelope removed.
    print(result.raw)  # The original AIMessage.


asyncio.run(main())
```

The input can be a string, a `PromptValue`, or a list of messages (including
tuples such as `("human", "...")`). Message inputs get the instructions as a
system message.

## Add it to an agent

```python
from langchain.agents import create_agent

from xstructured.agents import XStructuredMiddleware

agent = create_agent(
    "openai:gpt-5-mini",
    tools=[],
    middleware=[XStructuredMiddleware(Contact)],
)


async def extract(message: str) -> Contact:
    state = await agent.ainvoke({"messages": [("human", message)]})
    return state["structured_response"].structured
```

The agent keeps its tools and loop; the middleware validates its final answer.
See [Agents and Deep Agents](../integrations/agents.md).

## Parse a chain's output

When you build the prompt yourself, put the parser's format instructions in it
and end the chain with the parser:

```python
from langchain_core.prompts import ChatPromptTemplate

from xstructured import XStructuredOutputParser

parser = XStructuredOutputParser(Contact)
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You extract contact details.\n\n{format_instructions}"),
        ("human", "{message}"),
    ]
).partial(format_instructions=parser.get_format_instructions())
chain = prompt | init_chat_model("openai:gpt-5-mini") | parser


async def parse(message: str) -> Contact:
    result = await chain.ainvoke({"message": message})
    return result.structured
```

## Stream text and data

```python
from xstructured import StreamEventKind


async def stream(message: str) -> None:
    model = init_chat_model("openai:gpt-5-mini")
    extractor = with_xstructured_output(model, Contact)
    async for event in extractor.astream(message):
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

## Test without a provider

`ScriptedChatModel` from `xstructured.testing` replays responses, so tests and
examples run offline:

```python
from xstructured.testing import ScriptedChatModel

model = ScriptedChatModel.of(
    'Done. <xstructured>{"name": "Priya", "email": "p@example.com"}'
    "</xstructured>"
)
```

See [Testing](../guide/testing.md). Next, read the
[user guide](../guide/index.md) or browse the [examples](../examples/index.md).
