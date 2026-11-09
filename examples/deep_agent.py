"""Validate the final answer of a Deep Agents research agent.

``create_deep_agent`` builds a planning agent with sub-agents and a virtual
filesystem on top of LangChain's agent runtime, so ``XStructuredMiddleware``
plugs into it exactly as it does into ``create_agent``.

Run it with ``uv run python examples/deep_agent.py``.
"""

from __future__ import annotations

import asyncio

from deepagents import create_deep_agent
from pydantic import BaseModel, Field

from _shared import banner, chat_model
from xstructured.agents import XStructuredMiddleware

SCRIPTED_REPLY = (
    "Here is a concise summary of retrieval-augmented generation (RAG).\n"
    "<xstructured>"
    '{"topic": "Retrieval-augmented generation", "key_points": ['
    '"RAG grounds model answers in retrieved documents instead of '
    'retraining.", '
    '"Answer quality depends mostly on retrieval quality, chunking, and '
    'reranking.", '
    '"Evaluation needs both retrieval metrics and answer faithfulness '
    'checks."], '
    '"open_questions": ["How should conflicting sources be resolved?"]}'
    "</xstructured>"
)


QUESTION = "Summarize retrieval-augmented generation in three key points."


class ResearchSummary(BaseModel):
    """A short research summary."""

    topic: str
    key_points: list[str] = Field(min_length=1, max_length=5)
    open_questions: list[str] = Field(default_factory=list)


async def main() -> None:
    async with chat_model(SCRIPTED_REPLY) as model:
        agent = create_deep_agent(
            model=model,
            system_prompt="You are a careful research assistant.",
            middleware=[XStructuredMiddleware(ResearchSummary)],
        )
        state = await agent.ainvoke({"messages": [("human", QUESTION)]})

    banner("Deep agent research summary")
    summary = state["structured_response"].structured
    print(f"Topic: {summary.topic}")
    for point in summary.key_points:
        print(f"- {point}")
    print(f"Open questions: {summary.open_questions}")


if __name__ == "__main__":
    asyncio.run(main())
