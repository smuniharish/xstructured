# LangChain Runnables

`with_xstructured_output(runnable, schema)` returns an `XStructuredRunnable`. It works
with any Runnable whose output is a string or a LangChain message: chat models, LLMs,
chains, and your own Runnables.

## Inputs

With `inject_instructions=True` (the default), the schema instructions are added to the
input before the wrapped Runnable runs:

| Input | How instructions are added |
| --- | --- |
| `str` | Appended after a blank line. |
| `PromptValue` | Becomes a chat prompt with the instructions as a system message. |
| Messages or message-like values (`BaseMessage`, `("human", "...")`, `{"role": ..., "content": ...}`) | Appended to a leading system message, or prepended as a new one. |
| Anything else, such as a dict | `TypeError` before the model is called. |

For dictionary inputs, for example a chain that starts with a prompt template, pass
`inject_instructions=False` and include `wrapper.instructions` (or
`schema_instructions(...)`) in your prompt. See the
[quickstart](../getting-started/quickstart.md#wrap-a-chain).

## Outputs

| Method | Returns |
| --- | --- |
| `invoke`, `ainvoke` | `XStructuredResult` |
| `batch`, `abatch` | a list of `XStructuredResult` (native LangChain batching, including `return_exceptions`) |
| `stream`, `astream` | ordered `StreamEvent` values ending with one `RESULT` event |
| `transform`, `atransform` (inside a composed chain) | the final `XStructuredResult` |

An `XStructuredResult` has:

| Field | Meaning |
| --- | --- |
| `content` | The response text with every envelope removed. |
| `structured` | The validated value. |
| `raw` | The wrapped Runnable's output; for streams of message chunks, the merged message. |
| `raw_text`, `json_text` | The response text, and the exact JSON that validated. |
| `recovered`, `repaired`, `repair_attempts` | How the value was obtained. |
| `schema_name` | The matched name, for named schemas. |
| `metadata` | Fingerprint, envelope count, timing, and message metadata. |

## Composition

The wrapper is a regular Runnable, so LangChain's tools apply:

```python
from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from xstructured import with_xstructured_output


class Summary(BaseModel):
    title: str
    bullets: list[str]


gpt = init_chat_model("openai:gpt-5-mini")
claude = init_chat_model("anthropic:claude-sonnet-4-5")
primary = with_xstructured_output(gpt, Summary)
backup = with_xstructured_output(claude, Summary)

robust = primary.with_retry(stop_after_attempt=2).with_fallbacks([backup])
summaries = robust.batch(["Summarize document A", "Summarize document B"])
```

In a sequence, downstream steps receive the `XStructuredResult`, whether the chain is
invoked or streamed:

```python
from langchain_core.runnables import RunnableLambda

titles = primary | RunnableLambda(lambda result: result.structured.title)
```

## Typing

`with_xstructured_output` is fully typed. Type checkers infer the value type from the
schema:

```python
from langchain_core.runnables import RunnableLambda


def respond(question: str) -> str:
    return "..."


wrapper = with_xstructured_output(RunnableLambda(respond), Summary)
# XStructuredRunnable[str, Summary]: invoke(...).structured is a Summary

many = with_xstructured_output(RunnableLambda(respond), Summary, multiple=True)
# XStructuredRunnable[str, list[Summary]]
```

Named envelopes produce `dict[str, Any]`; named schemas without envelopes produce `Any`,
because the value can be any of the named types.

## Tracing and callbacks

Each call is one traced run with the wrapped Runnable as a child run, and
`with_config(run_name=..., tags=..., metadata=...)` works as usual. See
[Observability](../guide/observability.md).
