"""A small LangGraph workflow with a validated structured node."""

from __future__ import annotations

from typing import TypedDict

from _shared import explabs_chat_model, print_result_header, require_env, require_package

require_package("langgraph", extra_group="examples")
require_env("EXPLABS_API_KEY")

from langchain_core.messages import HumanMessage  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from xstructured import with_xstructured_output  # noqa: E402


class Triage(BaseModel):
    """The routing decision made by the workflow."""

    priority: str
    team: str
    summary: str


class WorkflowState(TypedDict):
    request: str
    triage: Triage


def main() -> None:
    triage = with_xstructured_output(explabs_chat_model(), Triage)
    graph = StateGraph(WorkflowState)

    def triage_request(state: WorkflowState) -> dict[str, Triage]:
        result = triage.invoke([HumanMessage(content=state["request"])])
        return {"triage": result.structured}

    graph.add_node("triage", triage_request)
    graph.add_edge(START, "triage")
    graph.add_edge("triage", END)
    workflow = graph.compile()

    result = workflow.invoke(
        {"request": "Checkout is failing for every customer in the EU.", "triage": None}
    )
    print_result_header("LangGraph incident triage")
    print(f"Validated route: {result['triage']!r}")


if __name__ == "__main__":
    main()
