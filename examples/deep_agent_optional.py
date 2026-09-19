"""Optional Deep Agents integration.

`deepagents` builds a "deep agent" (planning, sub-agents, and a virtual
filesystem) on top of LangGraph, and its compiled graph has the same
`{"messages": [...]}` invocation contract as `create_agent`. It is wrapped
with `with_xstructured_output` the same way, via a small adapter that
extracts the final message.

This example is entirely optional: it is skipped with a helpful message when
`deepagents` is not installed, and again when no provider API key is set.

    uv sync --group examples
    $env:EXPLABS_API_KEY = "..."
    uv run python examples/deep_agent_optional.py
"""

from __future__ import annotations

from collections.abc import Sequence

from _shared import explabs_chat_model, print_result_header, require_env, require_package

require_package("deepagents", extra_group="examples")
require_env("EXPLABS_API_KEY")

from deepagents import create_deep_agent  # noqa: E402
from langchain_core.messages import BaseMessage, HumanMessage  # noqa: E402
from langchain_core.runnables import RunnableLambda  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from xstructured import with_xstructured_output  # noqa: E402


class ResearchSummary(BaseModel):
    """A structured research summary produced by a deep agent."""

    topic: str
    key_points: list[str]
    open_questions: list[str] = []


def main() -> None:
    deep_agent = create_deep_agent(
        model=explabs_chat_model(),
        system_prompt="You are a careful research assistant.",
    )

    def _invoke(messages: Sequence[BaseMessage]) -> BaseMessage:
        state = deep_agent.invoke({"messages": list(messages)})
        return state["messages"][-1]

    summarizer = with_xstructured_output(RunnableLambda(_invoke), ResearchSummary)

    prompt = "Summarize the current state of retrieval-augmented generation in three key points."
    result = summarizer.invoke([HumanMessage(content=prompt)])

    print_result_header("Deep agent research summary")
    print(f"Structured summary: {result.structured!r}")


if __name__ == "__main__":
    main()
