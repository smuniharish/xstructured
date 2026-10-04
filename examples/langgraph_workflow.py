"""Route a LangGraph workflow on a validated triage decision.

The triage node calls a wrapped chat model and stores the validated ``Triage``
value in graph state; a conditional edge routes on its ``priority`` field.

Run it with ``uv run python examples/langgraph_workflow.py``.
"""

from __future__ import annotations

from typing import Literal

from _shared import banner, chat_model, require_packages

require_packages("langgraph")

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from xstructured import with_xstructured_output

SCRIPTED_REPLY = (
    "This is a customer-facing outage in one region.\n"
    "<xstructured>"
    '{"priority": "critical", "team": "payments", '
    '"summary": "Checkout fails for every customer in the EU."}'
    "</xstructured>"
)


class Triage(BaseModel):
    """The routing decision for an incoming request."""

    priority: Literal["low", "high", "critical"]
    team: str
    summary: str


class WorkflowState(BaseModel):
    """Graph state."""

    request: str
    triage: Triage | None = None
    action: str = ""


def main() -> None:
    triage = with_xstructured_output(chat_model(SCRIPTED_REPLY), Triage)

    def triage_request(state: WorkflowState) -> dict[str, Triage]:
        return {
            "triage": triage.invoke([HumanMessage(state.request)]).structured
        }

    def route(state: WorkflowState) -> Literal["page_on_call", "open_ticket"]:
        return (
            "page_on_call"
            if state.triage and state.triage.priority == "critical"
            else "open_ticket"
        )

    def page_on_call(state: WorkflowState) -> dict[str, str]:
        team = state.triage.team if state.triage else "unknown"
        return {"action": f"Paged the {team} on-call engineer"}

    def open_ticket(state: WorkflowState) -> dict[str, str]:
        team = state.triage.team if state.triage else "triage"
        return {"action": f"Opened a ticket in the {team} queue"}

    graph = StateGraph(WorkflowState)
    graph.add_node("triage", triage_request)
    graph.add_node("page_on_call", page_on_call)
    graph.add_node("open_ticket", open_ticket)
    graph.add_edge(START, "triage")
    graph.add_conditional_edges("triage", route)
    graph.add_edge("page_on_call", END)
    graph.add_edge("open_ticket", END)
    workflow = graph.compile()

    final = workflow.invoke(
        {"request": "Checkout is failing for every customer in the EU."}
    )

    banner("LangGraph incident triage")
    print(f"Triage: {final['triage']!r}")
    print(f"Action: {final['action']}")


if __name__ == "__main__":
    main()
