# Single-agent extraction

[`examples/single_agent_extraction.py`](https://github.com/xstructured/xstructured/blob/main/examples/single_agent_extraction.py)
wraps one `create_agent` agent with `with_xstructured_output` to extract a
`ContactInfo` (`name`, `email`, optional `company`) from a natural-language
message.

## Core pattern

```python
from collections.abc import Sequence
import os

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from xstructured import with_xstructured_output


class ContactInfo(BaseModel):
    name: str
    email: str
    company: str | None = None


model = ChatOpenAI(
    model=os.environ.get("EXPLABS_MODEL", "gpt-5.6-luna"),
    api_key=os.environ["EXPLABS_API_KEY"],
    base_url=os.environ.get(
        "EXPLABS_BASE_URL",
        "https://api.experientiallabs.ai/v1",
    ),
)
agent = create_agent(model=model, tools=[])


def final_message(messages: Sequence[BaseMessage]) -> BaseMessage:
    state = agent.invoke({"messages": list(messages)})
    return state["messages"][-1]


extractor = with_xstructured_output(
    RunnableLambda(final_message),
    ContactInfo,
)
result = extractor.invoke(
    [HumanMessage(content="Reach Priya Shah at priya.shah@example.com.")]
)

print(result.text)
print(result.structured.email)
```

The model factory in this snippet is an application concern. The full
repository example uses an OpenAI-compatible model configured with
`EXPLABS_API_KEY`, `EXPLABS_MODEL`, and `EXPLABS_BASE_URL`; xstructured itself
does not contain provider credentials or provider-specific runtime code.

```bash
uv sync --group examples
export EXPLABS_API_KEY="..."
export EXPLABS_MODEL="gpt-5.6-luna"
export EXPLABS_BASE_URL="https://api.experientiallabs.ai/v1"
uv run python examples/single_agent_extraction.py
```

It demonstrates the `RunnableLambda` adapter needed to bridge
`create_agent`'s `{"messages": [...]}` dict state to the plain
`Sequence[BaseMessage]` in / `BaseMessage` out contract `xstructured`
expects -- see [the LangChain integration guide](../integrations/langchain.md)
for why this adapter is necessary.

Without `EXPLABS_API_KEY` set, the script prints a short explanation and
exits with status `0`.

## Live run output

The following output was captured from a live provider run. This model returned
only the structured envelope, so `result.text` was empty; that is valid and
demonstrates that natural-language text is optional.

```text
=== Single-agent extraction ===
Natural language reply: ''
Structured output: ContactInfo(name='Priya Shah', email='priya.shah@example.com', company='Acme Corp')
Recovered from imperfect JSON: False
```
