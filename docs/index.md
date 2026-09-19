# xstructured

`xstructured` is a schema-guided structured output layer for
[LangChain v1](https://docs.langchain.com/oss/python/releases/langchain-v1)
`Runnable`s and agents. It wraps any chat model, `create_agent` agent, or
custom `Runnable` so its natural-language output is turned into a validated
[Pydantic v2](https://docs.pydantic.dev/latest/) object.

It does not call a model provider itself, and it is not a replacement for
`create_agent`'s built-in `output_schema` -- see
[Why wrap instead of `output_schema`?](integrations/langchain.md#why-wrap-instead-of-output_schema)
for the precise boundary.

## What it adds on top of a Runnable

- **Envelope protocol** -- a delimited region (`<xstructured>...</xstructured>`
  by default) that reliably separates structured JSON from surrounding
  natural-language text, even mid-stream.
- **Conservative recovery** -- markdown code fences and prose around a JSON
  payload are stripped without altering JSON syntax, before validation.
- **Ordered streaming** -- `.stream()`/`.astream()` yield `TEXT_DELTA`,
  `STRUCTURED_START`, `STRUCTURED_DELTA`, `STRUCTURED_END`, and `RESULT`
  events in the order the underlying text arrived.
- **Schema fingerprinting** -- a deterministic hash of a schema's JSON
  Schema, for cache keys, telemetry, and detecting schema drift.

## Start here

- [Installation](getting-started/installation.md)
- [Quickstart](getting-started/quickstart.md)
- [Concepts](concepts/index.md)
- [Architecture overview](architecture/overview.md)
- [Security](security.md)
- [Benchmarks](benchmarks.md)
- [LangChain integration](integrations/langchain.md)
- [Examples](examples/index.md)
- [API reference](api/index.md)
