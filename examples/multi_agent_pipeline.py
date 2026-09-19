"""Multi-agent pipeline: an extractor agent feeding a reviewer agent.

Two independent `create_agent` agents are each wrapped with
`with_xstructured_output` against their own schema. The first agent's
validated structured output is serialized and handed to the second agent,
which reviews it and returns its own validated verdict. This demonstrates
composing several xstructured-wrapped agents into a pipeline, not a single
shared agent loop.

Requires EXPLABS_API_KEY. Install the example dependencies first:

    uv sync --group examples
    $env:EXPLABS_API_KEY = "..."
    uv run python examples/multi_agent_pipeline.py
"""

from __future__ import annotations

from collections.abc import Sequence

from _shared import explabs_chat_model, print_result_header, require_env, require_package

require_package("langchain", extra_group="examples")
require_env("EXPLABS_API_KEY")

from langchain.agents import create_agent  # noqa: E402
from langchain_core.messages import BaseMessage, HumanMessage  # noqa: E402
from langchain_core.runnables import RunnableLambda  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from xstructured import with_xstructured_output  # noqa: E402


class ExpenseClaim(BaseModel):
    """A single expense line item extracted from a free-text report."""

    amount_usd: float
    category: str
    description: str


class ClaimReview(BaseModel):
    """A reviewer agent's verdict on an extracted expense claim."""

    approved: bool
    reason: str


def _agent_runnable(tools: list | None = None):
    agent = create_agent(model=explabs_chat_model(), tools=tools or [])

    def _invoke(messages: Sequence[BaseMessage]) -> BaseMessage:
        state = agent.invoke({"messages": list(messages)})
        return state["messages"][-1]

    return RunnableLambda(_invoke)


def main() -> None:
    extractor = with_xstructured_output(_agent_runnable(), ExpenseClaim)
    reviewer = with_xstructured_output(_agent_runnable(), ClaimReview)

    report = "Taxi from the airport to the client site cost $63.50."
    claim_result = extractor.invoke([HumanMessage(content=report)])

    print_result_header("Extractor agent")
    print(f"Structured claim: {claim_result.structured!r}")

    review_prompt = (
        "Review this expense claim for a standard corporate travel policy "
        f"(receipts required over $75, no alcohol): {claim_result.structured.model_dump_json()}"
    )
    review_result = reviewer.invoke([HumanMessage(content=review_prompt)])

    print_result_header("Reviewer agent")
    print(f"Structured review: {review_result.structured!r}")


if __name__ == "__main__":
    main()
