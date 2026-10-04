# LangGraph

Inside a LangGraph node, call the wrapper and store the validated value in graph state.
Conditional edges can then route on typed fields instead of parsing text.

```python
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from xstructured import with_xstructured_output


class Triage(BaseModel):
    priority: Literal["low", "high", "critical"]
    team: str
    summary: str


class State(BaseModel):
    request: str
    triage: Triage | None = None
    action: str = ""


triage = with_xstructured_output(init_chat_model("openai:gpt-5-mini"), Triage)


def triage_request(state: State) -> dict[str, Triage]:
    return {"triage": triage.invoke([HumanMessage(state.request)]).structured}


def route(state: State) -> Literal["page_on_call", "open_ticket"]:
    critical = state.triage is not None and state.triage.priority == "critical"
    return "page_on_call" if critical else "open_ticket"


def page_on_call(state: State) -> dict[str, str]:
    team = state.triage.team if state.triage else "on-call"
    return {"action": f"Paged {team}"}


def open_ticket(state: State) -> dict[str, str]:
    action = "Opened a ticket"
    if state.triage:
        action += f" for {state.triage.team}"
    return {"action": action}


graph = StateGraph(State)
graph.add_node("triage", triage_request)
graph.add_node("page_on_call", page_on_call)
graph.add_node("open_ticket", open_ticket)
graph.add_edge(START, "triage")
graph.add_conditional_edges("triage", route)
graph.add_edge("page_on_call", END)
graph.add_edge("open_ticket", END)
workflow = graph.compile()
```

Because the wrapper is a traced Runnable, it appears as a child run of the node in
LangSmith, and LangGraph's `stream_mode="messages"` still streams the model's tokens.

The complete script is in the [LangGraph workflow example](../examples/langgraph-workflow.md).
