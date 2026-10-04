"""Chain two agents, each with its own validated output.

An extractor agent turns a free-text expense report into an ``ExpenseClaim``;
a reviewer agent checks that claim against a policy and returns a
``ClaimReview``. Each agent is wrapped independently, so every hand-off
between agents is schema-validated.

Run it with ``uv run python examples/multi_agent_pipeline.py``.
"""

from __future__ import annotations

from collections.abc import Sequence

from _shared import banner, chat_model, require_packages

require_packages("langchain")

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field

from xstructured import with_xstructured_output

EXTRACTOR_REPLY = (
    "Extracted one transportation expense.\n"
    "<xstructured>"
    '{"amount_usd": 63.5, "category": "transportation", '
    '"description": "Taxi from the airport to the client site"}'
    "</xstructured>"
)
REVIEWER_REPLY = (
    "The claim is within policy.\n"
    "<xstructured>"
    '{"approved": true, '
    '"reason": "Under the $75 receipt threshold and not alcohol."}'
    "</xstructured>"
)
POLICY = "Receipts are required above $75. Alcohol is never reimbursed."


class ExpenseClaim(BaseModel):
    """One expense line item."""

    amount_usd: float = Field(gt=0)
    category: str
    description: str


class ClaimReview(BaseModel):
    """A reviewer's decision on an expense claim."""

    approved: bool
    reason: str


def agent_runnable(model: BaseChatModel, instructions: str) -> RunnableLambda:
    agent = create_agent(model=model, tools=[], system_prompt=instructions)

    def run(messages: Sequence[BaseMessage]) -> BaseMessage:
        return agent.invoke({"messages": list(messages)})["messages"][-1]

    return RunnableLambda(run)


def main() -> None:
    extractor = with_xstructured_output(
        agent_runnable(
            chat_model(EXTRACTOR_REPLY), "You extract expense claims."
        ),
        ExpenseClaim,
    )
    reviewer = with_xstructured_output(
        agent_runnable(
            chat_model(REVIEWER_REPLY), f"You review expenses. Policy: {POLICY}"
        ),
        ClaimReview,
    )

    claim = extractor.invoke(
        [HumanMessage("Taxi from the airport to the client site cost $63.50.")]
    ).structured
    review = reviewer.invoke(
        [HumanMessage(f"Review this claim: {claim.model_dump_json()}")]
    ).structured

    banner("Multi-agent pipeline")
    print(f"Claim:  {claim!r}")
    print(f"Review: {review!r}")


if __name__ == "__main__":
    main()
