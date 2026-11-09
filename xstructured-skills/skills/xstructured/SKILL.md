---
name: xstructured
description: >-
  Use this skill when an application needs natural-language text and
  Pydantic-validated data from the same LLM response with the xstructured
  package: wrapping a LangChain chat model, chain, or LangGraph graph with
  with_xstructured_output, adding XStructuredMiddleware to a create_agent or
  Deep Agents agent, using XStructuredOutputParser in a prompt | model | parser
  chain, streaming prose and a structured card to a UI, multiple or named
  payloads, bounded repair, validation context, OpenTelemetry tracing, and
  offline tests with ScriptedChatModel. Also use it when parsing fails with
  ParseError, RecoveryError, RepairError, or LimitExceededError. Do not use it
  to write a custom JsonDecoder, RecoveryStrategy, Observer, or other
  extension point (use xstructured-extend), or when only the structured value
  is needed and the provider's native structured output suffices.
license: Apache-2.0
compatibility: >-
  Python 3.12 or newer. Installs xstructured 1.x from PyPI; agents need
  xstructured[agents] or xstructured[deepagents], LangGraph nodes need
  xstructured[langgraph], tracing needs xstructured[otel].
  scripts/verify_setup.py runs offline in the project's Python environment.
metadata:
  version: "1.0.0"
  documentation: "https://xstructured.readthedocs.io"
---

# xstructured

xstructured asks a model to answer in prose and to put JSON inside an envelope,
`<xstructured>...</xstructured>`. It extracts the envelope, recovers
conservatively from Markdown fences or surrounding prose, validates the JSON
with Pydantic in JSON mode, and returns an `XStructuredResult` holding both the
prose (`result.content`) and the validated value (`result.structured`). Every
API is async-first: use `ainvoke`, `astream`, and `abatch`.

## Pick the attach mode

| The code has | Use | The value is in |
| --- | --- | --- |
| A chat model, chain, Runnable, or compiled graph | `with_xstructured_output(runnable, Schema)` | `(await wrapper.ainvoke(x)).structured` |
| `create_agent` or `create_deep_agent` | `XStructuredMiddleware(Schema)` from `xstructured.agents` | `state["structured_response"].structured` |
| A prompt template piped into a model | `XStructuredOutputParser(Schema)` | `(await chain.ainvoke(x)).structured` |
| Text from anywhere else | `StructuredParser(Schema, envelope=EnvelopeSpec())` | `.parse(text).value` |

## Workflow

Copy this checklist and keep it current:

```text
- [ ] 1. verify_setup.py passes
- [ ] 2. Schema is a Pydantic model with described fields
- [ ] 3. One attach mode chosen and wired once, at module level
- [ ] 4. Errors handled by type; repair bounded if used
- [ ] 5. Offline tests with ScriptedChatModel
- [ ] 6. Project tests and verify_setup.py pass again
```

1. From the project's Python environment, run this skill's setup check:
   `python scripts/verify_setup.py`. Fix every `FAIL` line first. Add
   `--agents` to require the agents extra, or `--json` for one JSON object.
2. Install only what is used: `pip install xstructured`, plus the
   `agents`, `deepagents`, `langgraph`, or `otel` extra.
3. Wire the attach mode once and reuse it; a wrapper holds no per-call state,
   so one instance serves concurrent tasks:

   ```python
   from langchain.chat_models import init_chat_model
   from pydantic import BaseModel, Field

   from xstructured import with_xstructured_output


   class Ticket(BaseModel):
       priority: str = Field(description="low, high, or critical")
       summary: str


   triage = with_xstructured_output(init_chat_model("openai:gpt-5-mini"), Ticket)


   async def handle(message: str) -> Ticket:
       result = await triage.ainvoke(message)
       return result.structured
   ```

   For agents, add the middleware and keep the agent's tools and prose:

   ```python
   from langchain.agents import create_agent

   from xstructured.agents import XStructuredMiddleware

   agent = create_agent(
       model, tools=tools, middleware=[XStructuredMiddleware(Ticket)]
   )
   # state = await agent.ainvoke({"messages": [("human", text)]})
   # ticket = state["structured_response"].structured
   ```

4. Catch `ParseError` (and its subclasses) where the value is used. Add
   repair only with an explicit budget: `repair=model,
   repair_config=RepairConfig(max_attempts=1)` for the wrapper, or
   `repair_config=` alone for the middleware.
5. Copy `assets/test_structured_output.py` into the project's tests and adapt
   the schema and replies. It runs offline with `ScriptedChatModel`.
6. Run the project's tests, then `python scripts/verify_setup.py` again. Do
   not report the task done until this second run passes.

## Read more only when needed

| Task | Read |
| --- | --- |
| Exact signatures, results, events, and errors | [references/api.md](references/api.md) |
| Agents, Deep Agents, LangGraph, output parsers, prompt templates, validation context | [references/integration.md](references/integration.md) |
| Streaming prose and a card to a UI, `StreamDecoder` | [references/streaming.md](references/streaming.md) |
| Envelopes, limits, recovery, repair, multiple and named payloads, `SchemaOptions` | [references/configuration.md](references/configuration.md) |
| Observers and OpenTelemetry spans | [references/observability.md](references/observability.md) |
| An error, a missing envelope, or an unexpected value | [references/troubleshooting.md](references/troubleshooting.md) |

## Rules

- **Async first.** Call `ainvoke`, `astream`, and `abatch` from async code;
  use `invoke` only where the caller is synchronous.
- **One contract.** Keep `<xstructured>` envelopes and let xstructured add the
  instructions. Do not also ask for JSON in a hand-written prompt.
- **Never weaken validation** to make a test pass: no `extra="allow"`, no
  `Any` fields, no raised limits, no disabled recovery checks.
- **Bound repair.** Repair is opt-in and limited by `RepairConfig.max_attempts`.
  Never loop on `ParseError` yourself.
- **Keep output out of logs.** `ParseError.text` holds the model output; it is
  never in the message. Log the message, not the text, when output may hold
  personal data.

## Gotchas

- `XStructuredMiddleware` lives in `xstructured.agents`, not the top-level
  package, and needs the `agents` extra.
- The final AI message in an agent's state keeps its envelope;
  `result.content` is the prose without it.
- With `inject_instructions=True` (the default) the wrapper accepts strings,
  prompt values, message lists, and `{"messages": [...]}` states. For other
  inputs pass `inject_instructions=False` and put `wrapper.instructions` in
  the prompt yourself, or use `XStructuredOutputParser`.
- Streaming events need the wrapper itself (`wrapper.astream`). Inside
  `wrapper | step`, only the final result flows downstream. Repair does not
  run while streaming events, and named envelopes cannot be streamed.
- `with_retry()`, `with_fallbacks()`, and `bind()` return LangChain wrappers
  around the wrapper; read `instructions` and `schema_fingerprint` from the
  original.
- A per-call validation context goes in the run config:
  `{"configurable": {CONTEXT_KEY: {...}}}`.
- `result.recovered` is `True` when the JSON came from a fence or prose; that
  is expected for many models and not an error.

## Files

- `scripts/verify_setup.py`: offline check of Python, the installed versions,
  parsing, the wrapper, streaming, and (with the extra) the middleware.
  `--json` prints one object. Exit codes are 0 (all pass) and 1 (a check
  failed).
- `assets/test_structured_output.py`: offline pytest template for a wrapper
  and an agent, using `ScriptedChatModel`.
