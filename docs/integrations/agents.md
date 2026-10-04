# Agents and Deep Agents

Agent graphs built with LangChain's `create_agent` or with Deep Agents'
`create_deep_agent` take and return `{"messages": [...]}` state. Wrap the agent at its
boundary with a small adapter that passes messages in and returns the final message:

```python
from collections.abc import Sequence

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

from xstructured import with_xstructured_output


class Contact(BaseModel):
    name: str
    email: str


agent = create_agent(
    model="openai:gpt-5-mini",
    tools=[],
    system_prompt="You extract contact details.",
)


def run_agent(messages: Sequence[BaseMessage]) -> BaseMessage:
    return agent.invoke({"messages": list(messages)})["messages"][-1]


extractor = with_xstructured_output(RunnableLambda(run_agent), Contact)
message = HumanMessage("Reach Priya Shah at priya.shah@example.com.")
result = extractor.invoke([message])
```

The wrapper adds its instructions as a system message in the input messages, so they
reach the model on every agent step, and validates the agent's final answer. The agent's
tools, middleware, and loop are unchanged.

## Deep Agents

`create_deep_agent` builds a planning agent with sub-agents and a virtual filesystem; the
same adapter applies:

```python
from deepagents import create_deep_agent

research_agent = create_deep_agent(
    model="openai:gpt-5-mini",
    system_prompt="You are a careful research assistant.",
)


def run_research(messages: Sequence[BaseMessage]) -> BaseMessage:
    return research_agent.invoke({"messages": list(messages)})["messages"][-1]


summarizer = with_xstructured_output(RunnableLambda(run_research), Contact)
```

## Things to keep in mind

- **Checkpointed agents.** With a checkpointer, the instruction system message becomes
  part of the conversation history on every call. Pass `inject_instructions=False` and
  put `extractor.instructions` in the agent's `system_prompt` instead.
- **Native structured output.** `create_agent(response_format=...)` makes the agent end
  with a structured response through tool calling or provider-native output. Prefer it
  when you only need the structured value; use xstructured when you also want the
  agent's prose, streaming of both, or one contract across providers.
- **Streaming.** A `RunnableLambda` adapter returns the final message only. To stream an
  agent's tokens, stream the agent graph with `stream_mode="messages"` and feed the final
  answer's text to a [`StreamDecoder`](../guide/streaming.md#decoding-a-stream-yourself).

Runnable examples: [single agent](../examples/single-agent-extraction.md),
[multi-agent pipeline](../examples/multi-agent-pipeline.md), and
[Deep Agents](../examples/deep-agent.md).
