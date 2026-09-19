# LangGraph workflow

[`examples/langgraph_workflow.py`](https://github.com/xstructured/xstructured/blob/main/examples/langgraph_workflow.py)
uses the current LangGraph `StateGraph`, `START`, and `END` APIs. The graph
keeps orchestration state separate from the validated `Triage` payload:

```python
from typing import TypedDict
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from xstructured import with_xstructured_output

class Triage(BaseModel):
    priority: str
    team: str
    summary: str

class State(TypedDict):
    request: str
    triage: Triage

triage = with_xstructured_output(model, Triage)
graph = StateGraph(State)
graph.add_node("triage", lambda state: {
    "triage": triage.invoke([HumanMessage(content=state["request"])]).structured
})
graph.add_edge(START, "triage")
graph.add_edge("triage", END)
workflow = graph.compile()
```

The complete script uses the repository's `EXPLABS_API_KEY`, `EXPLABS_MODEL`,
and `EXPLABS_BASE_URL` convention and skips cleanly without credentials.

## Live run output

```text
=== LangGraph incident triage ===
Validated route: Triage(priority='critical', team='Payments/Checkout', summary='Checkout is failing for every customer in the EU, indicating a widespread regional outage.')
```

The graph owns orchestration state; the `Triage` value is validated before it
is written into the final graph state.
