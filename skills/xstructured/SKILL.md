---
name: xstructured
description: Adds schema-validated Pydantic v2 output to LangChain v1 chat models, chains, Runnables, and agents with the xstructured Python package, returning natural-language text and validated data from one LLM response. Use when code uses or should use with_xstructured_output, StructuredParser, StreamDecoder, or <xstructured>...</xstructured> envelopes; when parsing JSON out of model text, streaming text plus structured data to a UI, validating create_agent, Deep Agents, or LangGraph output, returning multiple or named payloads, or adding bounded LLM repair.
license: Apache-2.0
compatibility: Python 3.12+ with the xstructured package (depends on langchain-core and pydantic v2). Live model calls need a configured LangChain chat model.
metadata:
  author: S MUNI HARISH
  version: "0.1.0"
  repository: https://github.com/smuniharish/xstructured
  documentation: https://xstructured.readthedocs.io
---

# xstructured

`xstructured` wraps a LangChain Runnable so one model response yields both prose and a
Pydantic-validated value. The model writes its answer and places JSON inside an envelope
(`<xstructured>...</xstructured>`); the wrapper adds instructions, extracts the envelope,
recovers conservatively from Markdown or prose, validates with Pydantic in JSON mode, and
returns an `XStructuredResult`.

## Decide whether it fits

Use xstructured when the application needs:

- natural-language text **and** typed data from the same response;
- a typed result from an existing chain, custom Runnable, or agent graph without
  rebuilding it;
- streaming of text deltas plus a validated value to a UI;
- one response contract across providers, including models without native structured
  output;
- explicit limits and typed errors for untrusted model output.

Prefer LangChain's native features when only the structured value is needed:
`model.with_structured_output(Schema)` for chat models, or
`create_agent(..., response_format=Schema)` for agents.

## Workflow

1. Confirm the environment: Python 3.12+, `langchain-core` 1.x, Pydantic v2, and
   `xstructured` installed (`pip install xstructured` or `uv add xstructured`).
2. Define the schema as a Pydantic model. Constrain it (`Literal`, `Field(ge=..., max_length=...)`,
   `extra="forbid"`) so validation, not application code, rejects bad output.
3. Pick the integration pattern from [references/integration.md](references/integration.md):
   chat model, chain with a prompt template, agent adapter, or LangGraph node.
4. Wrap with `with_xstructured_output(runnable, Schema, ...)`. Choose `multiple=True`,
   named schemas, or `multiple_envelopes=True` only when one response must carry several
   values.
5. Consume `result.structured` in code and `result.content` for people. For UIs, use
   `stream()` events; see [references/streaming.md](references/streaming.md).
6. Handle `ParseError` subclasses deliberately; see
   [references/troubleshooting.md](references/troubleshooting.md).
7. Test offline with a fake model (below) before calling a live provider.

## Core patterns

Wrap a chat model or any Runnable that returns text or messages:

```python
from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from xstructured import with_xstructured_output


class Contact(BaseModel):
    name: str
    email: str


model = init_chat_model("openai:gpt-5-mini")
extractor = with_xstructured_output(model, Contact)
result = extractor.invoke("Reach Priya Shah at priya.shah@example.com.")
contact = result.structured  # Contact instance
reply = result.content  # prose with the envelope removed
```

Parse text that already exists, without LangChain:

```python
from xstructured import StructuredParser

parser = StructuredParser(Contact)
parsed = parser.parse('Sure! {"name": "Priya", "email": "p@example.com"}')
assert parsed.recovered  # JSON was found inside surrounding prose
```

Test offline with LangChain's fake chat model:

```python
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

reply_text = (
    'Done. <xstructured>{"name": "Priya", "email": "p@example.com"}'
    "</xstructured>"
)
fake = GenericFakeChatModel(messages=iter([AIMessage(content=reply_text)]))
result = with_xstructured_output(fake, Contact).invoke("q")
assert result.structured.name == "Priya"
```

## Rules

- Wrap the **whole** chain or agent boundary, so the instructions reach the model and the
  final output is validated.
- Inputs must be a string, `PromptValue`, or message list. For dict inputs (prompt
  templates, agent state), pass `inject_instructions=False` and put
  `schema_instructions(Schema, envelope=EnvelopeSpec())` or `wrapper.instructions` in the
  prompt; otherwise the wrapper raises `TypeError` before calling the model.
- Adapt `create_agent` and `create_deep_agent` graphs with a `RunnableLambda` that passes
  messages in and returns `state["messages"][-1]`.
- Never parse model JSON by slicing strings or with ad hoc regexes; use `StructuredParser`
  or the wrapper.
- Keep validation strict. Do not catch and ignore `ParseError`, loosen schemas to make
  bad output pass, or raise limits without a measured need.
- Use `repair=` only as an explicit, bounded fallback (`RepairConfig(max_attempts=...)`),
  never as a substitute for clear instructions.
- Treat validated values as untrusted: apply authorization and business rules before side
  effects.
- Do not edit xstructured's source to work around behavior; configure it through its
  public API ([references/api.md](references/api.md)).

## References

- [references/api.md](references/api.md): public API, result fields, and metadata.
- [references/integration.md](references/integration.md): chat models, chains, agents,
  Deep Agents, LangGraph, and composition.
- [references/streaming.md](references/streaming.md): stream events, decoding, and limits.
- [references/configuration.md](references/configuration.md): limits, recovery, multiple
  payloads, and repair.
- [references/troubleshooting.md](references/troubleshooting.md): errors, causes, and
  fixes.
