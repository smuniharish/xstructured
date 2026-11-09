"""Chain two agents, each with its own validated output.

An extractor agent turns a free-text expense report into an ``ExpenseClaim``;
a reviewer agent checks that claim against a policy and returns a
``ClaimReview``. Each agent has its own ``XStructuredMiddleware``, so every
hand-off between agents is schema-validated.

Run it with ``uv run python examples/multi_agent_pipeline.py``.
"""

from __future__ import annotations

import asyncio

from langchain.agents import create_agent
from pydantic import BaseModel, Field

from _shared import banner, chat_model
from xstructured.agents import XStructuredMiddleware

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


async def main() -> None:
    async with (
        chat_model(EXTRACTOR_REPLY) as extractor_model,
        chat_model(REVIEWER_REPLY) as reviewer_model,
    ):
        extractor = create_agent(
            extractor_model,
            system_prompt="You extract expense claims.",
            middleware=[XStructuredMiddleware(ExpenseClaim)],
        )
        reviewer = create_agent(
            reviewer_model,
            system_prompt=f"You review expenses. Policy: {POLICY}",
            middleware=[XStructuredMiddleware(ClaimReview)],
        )

        extracted = await extractor.ainvoke(
            {
                "messages": [
                    (
                        "human",
                        "Taxi from the airport to the client cost $63.50.",
                    )
                ]
            }
        )
        claim = extracted["structured_response"].structured
        reviewed = await reviewer.ainvoke(
            {
                "messages": [
                    ("human", f"Review this claim: {claim.model_dump_json()}")
                ]
            }
        )
        review = reviewed["structured_response"].structured

    banner("Multi-agent pipeline")
    print(f"Claim:  {claim!r}")
    print(f"Review: {review!r}")


if __name__ == "__main__":
    asyncio.run(main())
