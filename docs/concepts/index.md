# Concepts

`xstructured` is built from four small, independently useful layers:

1. **[Schema](schema.md)** -- introspect a Pydantic v2 target into a
   `TypeAdapter` and JSON Schema (`inspect_schema`), turn that into a
   deterministic hash (`fingerprint_schema`) and into instructions for a
   model prompt (`schema_instructions`).
2. **[Envelope](envelope.md)** -- a streaming scanner that finds one
   delimited region (`<xstructured>...</xstructured>` by default) inside
   arbitrary, chunked text.
3. **[Parsing and recovery](parsing.md)** -- `StructuredParser` turns text
   into a schema-validated Python object, trying a small number of
   conservative, order-preserving recovery candidates (markdown fences,
   surrounding prose) before giving up.
4. **[Streaming](streaming.md)** -- `StreamDecoder` turns a live stream of
   text chunks into ordered `TEXT_DELTA` / `STRUCTURED_*` / `RESULT` events,
   so a caller can render prose and structured data as they arrive.

The [LangChain integration](../integrations/langchain.md) composes all four
into a single `with_xstructured_output(runnable, schema)` wrapper, but each
layer is public and independently usable.

Focused guidance covers [repair versus recovery](repair.md),
[multiple-payload behavior](multiple-payloads.md), and
[security boundaries](../security.md).

See the [architecture overview](../architecture/overview.md) for how these
pieces fit together, and the [API reference](../api/index.md) for exact
signatures.
