# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Unreleased

The first release.

### Added

- `with_xstructured_output` and `XStructuredRunnable`: wrap any LangChain v1 Runnable that
  returns text or messages, inject schema instructions, and return an `XStructuredResult`
  with the prose, the validated value, the raw output, and metadata.
- Native Runnable behavior: `invoke`, `ainvoke`, `batch`, `abatch`, `stream`, `astream`,
  tracing with the wrapped and repair Runnables as child runs, and composition in which
  downstream steps receive the final result whether a chain is invoked or streamed.
- Instruction injection for strings, prompt values, and message-like sequences, with a
  clear `TypeError` for inputs that cannot carry instructions.
- `StructuredParser`: envelope extraction, conservative recovery (Markdown fences and
  surrounding prose), strict JSON decoding, and Pydantic validation in JSON mode.
- Envelopes: `EnvelopeSpec`, the incremental `EnvelopeScanner`, and named envelopes such as
  `<xstructured name="finding">`.
- Multiple values: JSON arrays (`multiple=True`), named schemas with a
  `{"schema": ..., "payload": ...}` discriminator, and separately named envelopes
  (`multiple_envelopes=True`).
- Streaming: `StreamDecoder` and ordered `StreamEvent` values (`TEXT_DELTA`,
  `STRUCTURED_START`, `STRUCTURED_DELTA`, `STRUCTURED_END`, `RESULT`).
- Opt-in, bounded LLM-assisted repair with `RepairConfig`.
- Schema helpers: `inspect_schema`, `schema_instructions`, `fingerprint_schema`,
  `canonical_schema_json`, and `inspect_named_schemas`.
- Typed results and errors: `ParseResult`, `XStructuredResult`, and the `XStructuredError`
  hierarchy, including `LimitExceededError`, `RecoveryError`, and `RepairError`.
- Type inference: `StructuredParser(Model)` and `with_xstructured_output(runnable, Model)`
  infer the value type, including `list[Model]` for `multiple=True`.
- An offline benchmark comparing plain JSON, LangChain's parsers, and xstructured.
- Example scripts that run offline with a scripted model or live against the Experiential
  Labs API, and an Agent Skill for AI coding agents.

### Security

- Input, envelope, payload, and nesting limits, enforced in linear time.
- Duplicate keys, `NaN`, `Infinity`, and overflowing numbers are rejected.
- Exception messages never contain model output.

[0.1.0]: https://github.com/smuniharish/xstructured/commits/master
