"""Give a LangChain agent a validated final answer.

``XStructuredMiddleware`` adds the schema instructions to every model call of
a ``create_agent`` agent. Tool-calling turns run as usual; the final answer is
validated and stored in the agent state as ``structured_response``.

Run it with ``uv run python examples/single_agent_extraction.py``.
"""

from __future__ import annotations

import asyncio

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from pydantic import BaseModel

from _shared import banner, chat_model
from xstructured.agents import XStructuredMiddleware

LOOKUP = AIMessage(
    content="",
    tool_calls=[
        {"name": "lookup_company", "args": {"name": "Priya Shah"}, "id": "1"}
    ],
)
SCRIPTED_REPLY = (
    "I found one contact in your message.\n\n"
    "<xstructured>"
    '{"name": "Priya Shah", "email": "priya.shah@example.com", '
    '"company": "Acme Corp"}'
    "</xstructured>"
)


REQUEST = (
    "Please loop in Priya Shah (priya.shah@example.com) on the quarterly "
    "review. Confirm in one short sentence who you found."
)


class ContactInfo(BaseModel):
    """A contact extracted from free text."""

    name: str
    email: str
    company: str | None = None


@tool
def lookup_company(name: str) -> str:
    """Return the company a person works for, from the CRM."""
    return "Acme Corp" if name == "Priya Shah" else "unknown"


async def main() -> None:
    async with chat_model(LOOKUP, SCRIPTED_REPLY) as model:
        agent = create_agent(
            model,
            tools=[lookup_company],
            system_prompt=(
                "You extract contact details from messages. Look up the "
                "company of every person you find."
            ),
            middleware=[XStructuredMiddleware(ContactInfo)],
        )
        state = await agent.ainvoke({"messages": [("human", REQUEST)]})

    result = state["structured_response"]
    banner("Single-agent extraction")
    print(f"Reply:      {result.content.strip()!r}")
    print(f"Structured: {result.structured!r}")
    print(f"Tool calls: {sum(m.type == 'tool' for m in state['messages'])}")


if __name__ == "__main__":
    asyncio.run(main())
