# Deep agents (optional)

[`examples/deep_agent_optional.py`](https://github.com/xstructured/xstructured/blob/main/examples/deep_agent_optional.py)
applies the exact same `RunnableLambda` wrapping pattern to
[`deepagents`](https://github.com/langchain-ai/deepagents)'s
`create_deep_agent`, extracting a structured `ResearchSummary` (`topic`,
`key_points`, `open_questions`), since the deep agent produces the same kind
of `{"messages": [...]}` dict-based `Runnable` as `create_agent`.

## Core pattern

```python
from collections.abc import Sequence
import os

from deepagents import create_deep_agent
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from xstructured import with_xstructured_output


class ResearchSummary(BaseModel):
    topic: str
    key_points: list[str]
    open_questions: list[str] = []


model = ChatOpenAI(
    model=os.environ.get("EXPLABS_MODEL", "gpt-5.6-luna"),
    api_key=os.environ["EXPLABS_API_KEY"],
    base_url=os.environ.get(
        "EXPLABS_BASE_URL",
        "https://api.experientiallabs.ai/v1",
    ),
)
deep_agent = create_deep_agent(
    model=model,
    system_prompt="You are a careful research assistant.",
)


def final_message(messages: Sequence[BaseMessage]) -> BaseMessage:
    state = deep_agent.invoke({"messages": list(messages)})
    return state["messages"][-1]


summarizer = with_xstructured_output(
    RunnableLambda(final_message),
    ResearchSummary,
)
result = summarizer.invoke(
    [HumanMessage(content="Summarize retrieval-augmented generation.")]
)
print(result.structured)
```

```bash
uv sync --group examples
export EXPLABS_API_KEY="..."
export EXPLABS_MODEL="gpt-5.6-luna"
export EXPLABS_BASE_URL="https://api.experientiallabs.ai/v1"
uv run python examples/deep_agent_optional.py
```

`deepagents` is only ever imported by this example script -- it is not a
dependency of the `xstructured` package. If it is not installed, or if
`EXPLABS_API_KEY` is unset, the script prints a short explanation and exits
with status `0`, which is what makes it safe to run unconditionally in CI
as a smoke test.

See [Deep Agents](../integrations/deepagents.md) for the integration
rationale.

## Live run output

The following output was captured from a live provider run. Research wording
and the number of points vary with the model and current knowledge:

```text
=== Deep agent research summary ===
Structured summary: ResearchSummary(
    topic='Current state of retrieval-augmented generation',
    key_points=['RAG has become a mainstream method for grounding language models in private, proprietary, or frequently changing information, reducing dependence on costly model retraining and improving citation and traceability.', 'The main performance bottlenecks are now retrieval quality, document chunking, query formulation, context selection, and evaluation—not simply the choice of the underlying language model. Hybrid search, reranking, metadata filtering, and agentic or iterative retrieval are common approaches to address these issues.', 'RAG systems are increasingly moving beyond simple vector search toward multimodal, structured, and tool-using architectures, but they still face challenges involving latency, cost, stale or conflicting sources, context overload, security risks such as prompt injection, and reliably measuring factuality and end-to-end usefulness.'],
    open_questions=['How should RAG systems be evaluated consistently across domains, especially for factuality, usefulness, citation correctness, and robustness?', 'When does additional retrieval improve answers, and when does it introduce noise or increase the risk of misleading model-generated synthesis?', 'How can systems securely retrieve and use data while resisting poisoned documents, prompt injection, and unauthorized information disclosure?']
)
```