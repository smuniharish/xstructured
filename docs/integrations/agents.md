<!-- docs-test: run -->

# Agents and Deep Agents

`XStructuredMiddleware` gives an agent built with LangChain's `create_agent` or
Deep Agents' `create_deep_agent` a validated final answer, while the agent
keeps its tools, its loop, and its prose. Install it with the `agents` extra:

```bash
pip install "xstructured[agents]"      # create_agent
pip install "xstructured[deepagents]"  # create_deep_agent
```

## Add the middleware

```python
import asyncio

from langchain.agents import create_agent
from langchain_core.tools import tool
from pydantic import BaseModel

from xstructured.agents import XStructuredMiddleware
from xstructured.testing import ScriptedChatModel


class Contact(BaseModel):
    name: str
    email: str
    company: str


@tool
def lookup_company(email: str) -> str:
    """Return the company that owns an email domain."""
    return "Acme Corp"


model = ScriptedChatModel.of(
    "Priya Shah works at Acme Corp. <xstructured>"
    '{"name": "Priya Shah", "email": "priya.shah@example.com", '
    '"company": "Acme Corp"}</xstructured>'
)
agent = create_agent(
    model,
    tools=[lookup_company],
    system_prompt="You extract contact details.",
    middleware=[XStructuredMiddleware(Contact)],
)


async def main() -> None:
    state = await agent.ainvoke(
        {"messages": [("human", "Who is priya.shah@example.com?")]}
    )
    result = state["structured_response"]
    assert result.structured.company == "Acme Corp"
    assert result.content == "Priya Shah works at Acme Corp. "
    assert "<xstructured>" in state["messages"][-1].content


asyncio.run(main())
```

On every model call the middleware adds the schema instructions to the system
message. When the model answers without tool calls, the answer is parsed and
validated:

- `state["structured_response"]` is an
  [`XStructuredResult`](../api/results.md) with the validated value, the prose,
  and metadata.
- The final AI message in `state["messages"]` stays exactly as the model wrote
  it, so later turns see a consistent conversation; `result.content` is the
  prose with the envelope removed.
- Turns that call tools pass through unchanged.

`ScriptedChatModel` stands in for a real chat model here; pass any LangChain
chat model, such as `init_chat_model("openai:gpt-5-mini")`, in your
application.

## Deep Agents

`create_deep_agent` takes the same middleware:

```python
from deepagents import create_deep_agent


class Summary(BaseModel):
    title: str
    points: list[str]


research_agent = create_deep_agent(
    model=ScriptedChatModel.of(
        "Here is the summary. <xstructured>"
        '{"title": "RAG", "points": ["retrieve", "ground", "cite"]}'
        "</xstructured>"
    ),
    system_prompt="You are a careful research assistant.",
    middleware=[XStructuredMiddleware(Summary)],
)


async def research() -> Summary:
    state = await research_agent.ainvoke(
        {"messages": [("human", "Summarize RAG in three points.")]}
    )
    return state["structured_response"].structured


assert asyncio.run(research()).points == ["retrieve", "ground", "cite"]
```

## Options

`XStructuredMiddleware` accepts the same options as
[`with_xstructured_output`](langchain.md), except the ones that only apply to a
wrapped Runnable's input:

| Option | Effect |
| --- | --- |
| `envelope`, `multiple`, `multiple_envelopes` | Envelope and value shape, as for the wrapper. |
| `parser_config` | Size limits and recovery. An envelope is always required. |
| `schema_options` | Pydantic options such as `strict`, `extra`, and `context`. |
| `inject_instructions=False` | Leave the system message alone; put `middleware.instructions` in your own `system_prompt`. |
| `repair_config`, `repair_prompt` | Ask the agent's own model to correct an invalid final answer. |
| `renderer`, `extractor`, `recovery`, `decoder` | [Extension points](../guide/extension-points.md). |
| `observer` | One [observation](../guide/observability.md) per final answer. |

### Repair

With `repair_config`, an invalid final answer is sent back to the agent's model
with the problems found, up to `max_attempts` times. Only the repaired message
is kept in the state. A repair reply that calls tools counts as a failed
attempt, and `RepairError` is raised when the budget runs out.

```python
from xstructured import RepairConfig

repairing = create_agent(
    ScriptedChatModel.of(
        'Done. <xstructured>{"name": "Priya Shah"}</xstructured>',
        'Fixed. <xstructured>{"name": "Priya Shah", '
        '"email": "priya.shah@example.com", "company": "Acme"}'
        "</xstructured>",
    ),
    middleware=[
        XStructuredMiddleware(
            Contact, repair_config=RepairConfig(max_attempts=1)
        )
    ],
)
state = asyncio.run(
    repairing.ainvoke({"messages": [("human", "Who is Priya?")]})
)
assert state["structured_response"].repaired
```

### Validation context

Pass a Pydantic validation context per call through the run config, under
[`CONTEXT_KEY`](../api/output-parser.md):

```python
from xstructured import CONTEXT_KEY

config = {"configurable": {CONTEXT_KEY: {"tenant": "acme"}}}
```

`await agent.ainvoke(state, config)` hands `{"tenant": "acme"}` to your
validators as `info.context`.

## Wrapping a whole agent

`with_xstructured_output` also accepts a compiled agent or graph directly. It
reads the final AI message from the returned `{"messages": [...]}` state. Use
it when you want the wrapper's streaming events for the whole agent; use the
middleware when the structured value belongs in the agent's state. See
[LangGraph](langgraph.md).

## Native structured output

`create_agent(response_format=...)` ends the agent with a structured response
through tool calling or provider-native output. Prefer it when you need only
the structured value; use xstructured when you also want the agent's prose,
streaming of both, conservative recovery, or one contract across providers.

Runnable examples: [single agent](../examples/single-agent-extraction.md),
[multi-agent pipeline](../examples/multi-agent-pipeline.md), and
[Deep Agents](../examples/deep-agent.md).
