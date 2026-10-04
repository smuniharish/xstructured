"""Validate the final answer of a Deep Agents research agent.

``create_deep_agent`` builds a planning agent with sub-agents and a virtual
filesystem on top of LangGraph. Like ``create_agent``, it exchanges
``{"messages": [...]}`` state, so the same adapter pattern applies.

Run it with ``uv run python examples/deep_agent.py``.
"""

from __future__ import annotations

from collections.abc import Sequence

from _shared import banner, chat_model, require_packages

require_packages("deepagents")

from deepagents import create_deep_agent
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field

from xstructured import with_xstructured_output

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


class ResearchSummary(BaseModel):
    """A short research summary."""

    topic: str
    key_points: list[str] = Field(min_length=1, max_length=5)
    open_questions: list[str] = Field(default_factory=list)


def main() -> None:
    deep_agent = create_deep_agent(
        model=chat_model(SCRIPTED_REPLY),
        system_prompt="You are a careful research assistant.",
    )

    def run_agent(messages: Sequence[BaseMessage]) -> BaseMessage:
        return deep_agent.invoke({"messages": list(messages)})["messages"][-1]

    summarizer = with_xstructured_output(
        RunnableLambda(run_agent), ResearchSummary
    )
    result = summarizer.invoke(
        [
            HumanMessage(
                "Summarize retrieval-augmented generation in three key points."
            )
        ]
    )

    banner("Deep agent research summary")
    summary = result.structured
    print(f"Topic: {summary.topic}")
    for point in summary.key_points:
        print(f"- {point}")
    print(f"Open questions: {summary.open_questions}")


if __name__ == "__main__":
    main()
