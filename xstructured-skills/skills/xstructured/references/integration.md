# Integration

## Chat models and chains

`with_xstructured_output` wraps any Runnable whose output is a string, a
message, or a `{"messages": [...]}` state. It adds the instructions to the
input, calls the Runnable, and parses the reply.

```python
from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from xstructured import with_xstructured_output


class Summary(BaseModel):
    title: str
    bullets: list[str]


summarize = with_xstructured_output(
    init_chat_model("openai:gpt-5-mini"), Summary
)


async def summary(text: str) -> Summary:
    result = await summarize.ainvoke(f"Summarize:\n{text}")
    return result.structured
```

Inputs the default injector accepts: a string (instructions appended), a
`PromptValue` or a message list (instructions in the leading system message),
and a `{"messages": [...]}` state (the same, with the system message ID
`INSTRUCTIONS_MESSAGE_ID`). Messages already carrying the instructions are not
changed again.

The wrapper composes like any Runnable: `wrapper | step` passes the
`XStructuredResult` on, `abatch` runs in parallel, `with_retry` and
`with_fallbacks` work as usual.

## Prompt templates: the output parser

When the prompt is a `ChatPromptTemplate`, put the instructions in the
template and end the chain with `XStructuredOutputParser`:

```python
from langchain_core.prompts import ChatPromptTemplate

from xstructured import XStructuredOutputParser

parser = XStructuredOutputParser(Summary)
prompt = ChatPromptTemplate.from_messages(
    [("system", "Summarize.\n{format}"), ("human", "{text}")]
).partial(format=parser.get_format_instructions())
chain = prompt | init_chat_model("openai:gpt-5-mini") | parser
# result = await chain.ainvoke({"text": "..."})
```

The parser returns an `XStructuredResult` and has no repair; wrap the
template chain with `with_xstructured_output(..., inject_instructions=False)`
and include `wrapper.instructions` in the template when repair is needed.

## Agents and Deep Agents

Install `xstructured[agents]` or `xstructured[deepagents]` and add the
middleware. It adds the instructions to every model call's system message and
parses the final answer (the model reply without tool calls).

```python
from langchain.agents import create_agent

from xstructured import RepairConfig
from xstructured.agents import XStructuredMiddleware

agent = create_agent(
    "openai:gpt-5-mini",
    tools=[],
    middleware=[
        XStructuredMiddleware(
            Summary, repair_config=RepairConfig(max_attempts=1)
        )
    ],
)
# state = await agent.ainvoke({"messages": [("human", "...")]})
# state["structured_response"]  -> XStructuredResult[Summary]
```

- Tool-calling turns pass through unchanged.
- The final AI message stays as the model wrote it, envelope included.
- With `repair_config`, the agent's own model is asked to correct an invalid
  final answer; only the repaired message is kept. A repair reply that calls
  tools counts as a failed attempt.
- `create_deep_agent(..., middleware=[XStructuredMiddleware(Schema)])` works
  the same way.
- `create_agent(response_format=...)` is the alternative when only the value
  is needed and the provider supports native structured output.

Wrapping a compiled agent with `with_xstructured_output(agent, Schema)` also
works: the wrapper injects into `{"messages": [...]}` and reads the last AI
message of the returned state. Use it to get protocol stream events for the
whole agent; use the middleware when the value belongs in the agent state.

## LangGraph nodes

Install `xstructured[langgraph]`. Await the wrapper inside an async node and
store the typed value in state; conditional edges route on fields.

```python
async def triage(state: State) -> dict[str, Ticket]:
    result = await triage_model.ainvoke(state.messages)
    return {"ticket": result.structured}
```

The wrapper is a traced Runnable, so it appears as a child run of the node,
and `stream_mode="messages"` still streams the model's tokens. To read the
text of only some nodes in a `messages` stream, pass
`extractor=MessageTextExtractor(nodes={"writer"})`.

## Validation context

Validators that read `info.context` get a per-call context from the run
config; it replaces `SchemaOptions(context=...)` for that call. It works for
the wrapper, the output parser, and the middleware.

```python
from xstructured import CONTEXT_KEY

config = {"configurable": {CONTEXT_KEY: {"tenant": "acme"}}}
# await wrapper.ainvoke(text, config)
# await agent.ainvoke(state, config)
```

## Offline tests

```python
from xstructured.testing import ScriptedChatModel

model = ScriptedChatModel.of(
    'Done. <xstructured>{"title": "t", "bullets": []}</xstructured>'
)
```

Pass it anywhere a chat model goes, agents included; scripted `AIMessage`
replies may carry tool calls. `assets/test_structured_output.py` is a ready
template.
