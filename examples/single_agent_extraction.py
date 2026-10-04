"""Extract a validated contact record from a LangChain agent.

A ``create_agent`` graph takes and returns ``{"messages": [...]}`` state. A
small ``RunnableLambda`` adapts it to the message-in, message-out shape that
``with_xstructured_output`` wraps; the agent itself is unchanged.

Run it with ``uv run python examples/single_agent_extraction.py``.
"""

from __future__ import annotations

from collections.abc import Sequence

from _shared import banner, chat_model, require_packages

require_packages("langchain")

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

from xstructured import with_xstructured_output

SCRIPTED_REPLY = (
    "I found one contact in your message.\n\n"
    "<xstructured>"
    '{"name": "Priya Shah", "email": "priya.shah@example.com", '
    '"company": "Acme Corp"}'
    "</xstructured>"
)


class ContactInfo(BaseModel):
    """A contact extracted from free text."""

    name: str
    email: str
    company: str | None = None


def main() -> None:
    agent = create_agent(
        model=chat_model(SCRIPTED_REPLY),
        tools=[],
        system_prompt="You extract contact details from messages.",
    )

    def run_agent(messages: Sequence[BaseMessage]) -> BaseMessage:
        return agent.invoke({"messages": list(messages)})["messages"][-1]

    extractor = with_xstructured_output(RunnableLambda(run_agent), ContactInfo)
    result = extractor.invoke(
        [
            HumanMessage(
                "Please loop in Priya Shah (priya.shah@example.com) from Acme "
                "Corp on the quarterly review. Confirm in one short sentence "
                "who you found."
            )
        ]
    )

    banner("Single-agent extraction")
    print(f"Reply:      {result.content.strip()!r}")
    print(f"Structured: {result.structured!r}")
    print(f"Recovered:  {result.recovered}")


if __name__ == "__main__":
    main()
