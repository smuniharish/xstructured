# Multi-agent pipeline

[`examples/multi_agent_pipeline.py`](https://github.com/xstructured/xstructured/blob/main/examples/multi_agent_pipeline.py)
chains two independently wrapped agents: an extractor agent produces a
structured `ExpenseClaim` from a free-text expense report, and a reviewer
agent independently produces a structured `ClaimReview` verdict for that
claim, each validated with its own `with_xstructured_output` call and its
own schema.

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


class ExpenseClaim(BaseModel):
    amount_usd: float
    category: str
    description: str


class ClaimReview(BaseModel):
    approved: bool
    reason: str


model = ChatOpenAI(
    model=os.environ.get("EXPLABS_MODEL", "gpt-5.6-luna"),
    api_key=os.environ["EXPLABS_API_KEY"],
    base_url=os.environ.get(
        "EXPLABS_BASE_URL",
        "https://api.experientiallabs.ai/v1",
    ),
)


def agent_runnable(schema):
    agent = create_agent(model=model, tools=[])

    def final_message(messages: Sequence[BaseMessage]) -> BaseMessage:
        state = agent.invoke({"messages": list(messages)})
        return state["messages"][-1]

    return with_xstructured_output(
        RunnableLambda(final_message),
        schema,
    )


extractor = agent_runnable(ExpenseClaim)
reviewer = agent_runnable(ClaimReview)
claim = extractor.invoke(
    [HumanMessage(content="Taxi from the airport cost $63.50.")]
)
review = reviewer.invoke(
    [HumanMessage(content=f"Review this claim: {claim.structured.model_dump_json()}")]
)
print(claim.structured)
print(review.structured)
```

Each agent keeps its own schema and result boundary, while the application
controls how the validated output is passed to the next agent.

```bash
uv sync --group examples
export EXPLABS_API_KEY="..."
export EXPLABS_MODEL="gpt-5.6-luna"
export EXPLABS_BASE_URL="https://api.experientiallabs.ai/v1"
uv run python examples/multi_agent_pipeline.py
```

This demonstrates that `with_xstructured_output` composes naturally across
a pipeline of agents -- each wrapped agent is a self-contained,
independently testable `Runnable` -- rather than requiring a single
monolithic schema for an entire multi-step pipeline.

Without `EXPLABS_API_KEY` set, the script prints a short explanation and
exits with status `0`.

## Live run output

The following output was captured from a live provider run. Exact wording and
classification labels may vary on subsequent runs:

```text
=== Extractor agent ===
Structured claim: ExpenseClaim(amount_usd=63.5, category='Transportation', description='Taxi from the airport to the client site')

=== Reviewer agent ===
Structured review: ClaimReview(approved=True, reason='Approved: the $63.50 transportation expense is below the $75 receipt threshold and contains no alcohol.')
```