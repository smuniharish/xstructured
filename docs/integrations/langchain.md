# LangChain Runnables

`with_xstructured_output(runnable, schema)` returns an `XStructuredRunnable`. It works
with any Runnable whose output is a string, a LangChain message, or a
`{"messages": [...]}` state: chat models, LLMs, chains, LangGraph graphs, agents, and
your own Runnables. For `prompt | model` chains you assemble yourself,
[`XStructuredOutputParser`](#output-parser) is the alternative.

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
`schema_instructions(...)`) in your prompt, or end the chain with an
[`XStructuredOutputParser`](../getting-started/quickstart.md#parse-a-chains-output).

## Outputs

| Method | Returns |
| --- | --- |
| `ainvoke`, `invoke` | `XStructuredResult` |
| `abatch`, `batch` | a list of `XStructuredResult` (native LangChain batching, including `return_exceptions`) |
| `astream`, `stream` | ordered `StreamEvent` values ending with one `RESULT` event |
| `atransform`, `transform` (inside a composed chain) | the final `XStructuredResult` |

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


async def summarize() -> None:
    summaries = await robust.abatch(["Summarize A", "Summarize B"])
    print([summary.structured.title for summary in summaries])
```

In a sequence, downstream steps receive the `XStructuredResult`, whether the chain is
invoked or streamed:

```python
from langchain_core.runnables import RunnableLambda

titles = primary | RunnableLambda(lambda result: result.structured.title)
```

## Output parser

`XStructuredOutputParser` is a LangChain output parser. Use it when the prompt
is built separately, for example with a `ChatPromptTemplate`: add
`get_format_instructions()` to the prompt and put the parser last in the chain.

```python
from langchain_core.prompts import ChatPromptTemplate

from xstructured import CONTEXT_KEY, XStructuredOutputParser

parser = XStructuredOutputParser(Summary)
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You summarize documents.\n\n{format_instructions}"),
        ("human", "{document}"),
    ]
).partial(format_instructions=parser.get_format_instructions())
chain = prompt | gpt | parser


async def summarize_document(document: str) -> Summary:
    config = {"configurable": {CONTEXT_KEY: {"max_bullets": 5}}}
    result = await chain.ainvoke({"document": document}, config)
    return result.structured
```

The parser returns the same `XStructuredResult` as the wrapper and accepts the
parsing options (`envelope`, `parser_config`, `multiple`, `multiple_envelopes`,
`schema_options`, `renderer`, `recovery`, `decoder`). Use the wrapper instead
when you need repair, streaming events, or an observer.

## Validation context

Validators that read `info.context` get a per-call context from the run config
under `CONTEXT_KEY` (`"xstructured_context"`). It works for the wrapper, the
output parser, and the agent middleware, and replaces the default
`SchemaOptions(context=...)` for that call.

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
`with_config(run_name=..., tags=..., metadata=...)` works as usual. Pass an
`observer` for metrics and [OpenTelemetry](opentelemetry.md) spans. See
[Observability](../guide/observability.md).

## Customization

Every behavior of the wrapper is an [extension point](../guide/extension-points.md):
the instructions (`renderer`), where they go in the input (`injector`), how output text
is read (`extractor`), which substrings are tried (`recovery`), how JSON is decoded
(`decoder`), the repair input (`repair_prompt`), and telemetry (`observer`). Pydantic's
own options pass through with [`SchemaOptions`](../guide/configuration.md#pydantic-options).
