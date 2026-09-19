"""Single-agent structured extraction with xstructured.

`with_xstructured_output` wraps a `Runnable` that returns a string or a
LangChain `BaseMessage`, injects schema instructions, and validates the
result against a Pydantic model -- tolerating markdown fences and
conversational prose around the JSON payload.

A `create_agent` agent's compiled graph returns a `{"messages": [...]}`
state rather than a bare message, so it is adapted with a small
`RunnableLambda` that extracts the final message before wrapping.

Requires EXPLABS_API_KEY. Install the example dependencies first:

    uv sync --group examples
    $env:EXPLABS_API_KEY = "..."
    uv run python examples/single_agent_extraction.py
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


class ContactInfo(BaseModel):
    """A single contact extracted from unstructured text."""

    name: str
    email: str
    company: str | None = None


def _invoke_agent(messages: Sequence[BaseMessage]) -> BaseMessage:
    """Run the agent and return its final message.

    The agent receives *messages* including the SystemMessage that
    `with_xstructured_output` injects, so the schema instructions reach
    the model.
    """
    agent = create_agent(model=explabs_chat_model(), tools=[])
    state = agent.invoke({"messages": list(messages)})
    return state["messages"][-1]


def main() -> None:
    extractor = with_xstructured_output(RunnableLambda(_invoke_agent), ContactInfo)

    message = (
        "Please loop in Priya Shah (priya.shah@example.com) from Acme Corp on the quarterly review."
    )
    result = extractor.invoke([HumanMessage(content=message)])

    print_result_header("Single-agent extraction")
    print(f"Natural language reply: {result.content!r}")
    print(f"Structured output: {result.structured!r}")
    print(f"Recovered from imperfect JSON: {result.recovered}")


if __name__ == "__main__":
    main()
