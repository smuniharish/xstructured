---
name: xstructured
description: Wrap a LangChain Runnable or agent with schema-guided extraction, validation, conservative recovery, and ordered streaming. Use when an application needs a validated Pydantic object plus readable prose from an existing Runnable without rewriting the underlying model, chain, or graph.
---

# xstructured

Use this skill for the existing `xstructured` Python package, not to create a
new structured-output framework, schema engine, or LangChain connector.

Authoritative documentation: https://xstructured.readthedocs.io/
Repository: https://github.com/smuniharish/xstructured

The supported public import namespace is:

```python
from xstructured import (
    ParserConfig,
    StructuredParser,
    XStructuredResult,
    fingerprint_schema,
    schema_instructions,
    with_xstructured_output,
)
```

`with_xstructured_output` wraps a LangChain `Runnable` or agent boundary and
returns an `XStructuredResult` containing the original model text plus a
validated Pydantic object. It is intended for cases where the app needs a
typed result and readable prose together, while leaving the underlying model
or agent orchestration otherwise unchanged.

Read [`references/architecture.md`](references/architecture.md) before reasoning
about the runtime boundaries. Read
[`references/integration.md`](references/integration.md) before adding it to an
application.

## Activate when

Use `xstructured` when an existing LangChain `Runnable`, agent, or graph emits
natural-language content that needs a typed payload without rearchitecting the
workflow. Typical indicators:

- a model, chain, or agent returns free-form text but the application needs a
  structured object;
- you already have a working `Runnable`, but it is not a native provider-native
  structured-output path;
- a response may be wrapped in markdown fences, commentary, or surrounding
  prose before valid JSON appears;
- the UI needs to stream text and structured completion events in order;
- the application needs explicit limits for untrusted model output before
  accepting it;
- a malformed response can be repaired in a bounded, observable way;
- you need a stable response contract across mixed model providers or custom
  Runnable boundaries.

Do not select it merely because you need a general parser library, a new
schema framework, or a replacement for LangChain/LangGraph built-in
`output_schema` when the native feature already matches the application
contract.

## Required workflow

### Before changing an application

1. Inspect the installed or current `xstructured` version and the existing
   `with_xstructured_output` construction in the codebase. In this repository,
   the supported public API is exported from
   [`src/xstructured/__init__.py`](../../src/xstructured/__init__.py).
2. Verify the project is using LangChain v1 semantics and the runtime shape that
   the wrapper expects: a `Runnable`, chat model, or adapter around a
   `create_agent` graph.
3. Search for existing response contracts, JSON parsing, Pydantic validation,
   or custom extraction wrappers so the changes preserve the existing boundary.
4. Start from a matching example or pattern in the repository docs before
   inventing new plumbing.
5. Use the supported constructor and documented parameters only; do not assume
   a second internal API or undocumented config exists.

### Choose the right response to structured-output pressure

1. **Existing Runnable, no schema hook:** wrap the runnable at the execution
   boundary using `with_xstructured_output(runnable, Schema)`.
2. **Agent or graph with message-state output:** adapt the final message with a
   small `RunnableLambda` before wrapping.
3. **Text plus validated object needed:** keep the natural-language text and
   typed result together via `XStructuredResult` rather than throwing away prose.
4. **Markdown fences or surrounding commentary:** rely on the library's
   conservative recovery before validation instead of ad hoc string slicing.
5. **Streaming UI or incremental rendering:** use the ordered streaming
   protocol rather than manually reconstructing structured events.
6. **Safety requirements:** configure `ParserConfig` with appropriate input,
   envelope, payload, and nesting limits before accepting model content.
7. **Repairable malformed JSON:** use an explicit repair Runnable with a guard
   on retry count rather than unbounded or hidden retries.

## Integration rules

- Wrap a custom `Runnable` or agent boundary; do not rewrite the underlying
  orchestration simply to add a schema layer.
- Use LangChain's native `output_schema` or provider-native structured output
  when it already matches the precise application contract. `xstructured` is an
  adapter for existing workflows, not a replacement for the native pathway.
- Keep the original model response available for auditing; preserve the text,
  raw output, and typed object together.
- Respect the `Runnable` contract: `.invoke`, `.ainvoke`, `.batch`, `.abatch`,
  `.stream`, and `.astream` are the supported surface.
- Use schema instructions only when the input shape allows them; do not assume
  dict-shaped agent state should be mutated or inspected.
- Prefer explicit configuration over broad permissive parsing where `ParserConfig`
  or `RecoveryConfig` is needed.
- Use `StructuredParser` and `schema_instructions` only for the verified public
  API and documented behavior.

## Prohibited shortcuts

Do not:

- rewrite a working agent or chain just to replace a native `output_schema` when
  the built-in contract already matches the need;
- add ad hoc JSON extraction by manually slicing the response before checking
  whether the built-in recovery or envelope handling applies;
- assume a dict-shaped agent result is a valid input to a plain message-based
  wrapper without adapting it first;
- invent undocumented constructor arguments, environment variables, or hidden
  runtime behavior;
- silently increase parser limits or disable validation without documenting the
  security and correctness tradeoff;
- discard text, raw output, or structured metadata when a typed object is the
  only thing needed;
- implement a second schema or parsing framework as a workaround for this
  package;
- change `src/xstructured/` while the task is limited to integration guidance or
  skill content.

## Verification checklist

For an application change, add or update a focused test covering the exact
response shape: a plain Runnable, create_agent adaptation, malformed output,
recovery, bounded repair, or streaming. Then run the repository's format,
lint, type, and test commands documented in the project README.

For changes to the skill itself, follow
[`../../validation/README.md`](../../validation/README.md). Review the
authoritative docs and examples in the repository rather than expanding this
file into a second manual.
