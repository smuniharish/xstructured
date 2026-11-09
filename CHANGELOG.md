# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-11-09

### Added

- `XStructuredMiddleware` in `xstructured.agents`: a validated final answer
  for `create_agent` and Deep Agents, while the agent keeps its tools and
  prose. The result is in `state["structured_response"]`, and repair runs
  through the agent's own model.
- `XStructuredOutputParser`: an LCEL output parser that ends a
  `prompt | model | parser` chain and returns an `XStructuredResult`, with
  `get_format_instructions()` for the prompt.
- Extension points as abstract base classes, each with a default and a
  keyword on the wrapper, the middleware, and the parser:
  `InstructionRenderer`, `InstructionInjector`, `OutputTextExtractor`,
  `RecoveryStrategy`, `JsonDecoder`, `RepairPromptBuilder`, and `Observer`.
  The defaults are `DefaultInstructionRenderer`,
  `MessageInstructionInjector`, `MessageTextExtractor`,
  `ConservativeRecovery`, `StrictJsonDecoder`, and `DefaultRepairPrompt`.
- `SchemaOptions`: Pydantic validation options (`strict`, `extra`,
  `context`, `by_alias`, `by_name`, a `ConfigDict`) and JSON schema options
  (`schema_generator`, `ref_template`, `union_format`, `json_schema_mode`)
  pass straight through to Pydantic.
- A per-call validation context in the run config under `CONTEXT_KEY`.
- `OpenTelemetryObserver` in `xstructured.otel`: one span per wrapper call,
  stream, and agent run, with your own `TracerProvider`.
- `xstructured.testing`: `ScriptedChatModel` for offline tests, and contract
  suites for decoders, recovery strategies, injectors, extractors, and
  observers.
- `MessageTextExtractor` reads agent and LangGraph states, with a
  configurable `messages_key` and node filter.
- The `agents`, `langgraph`, `deepagents`, `otel`, and `all` extras.
- Python 3.15 support.
- Twelve async examples, including Deep Agents, an output parser chain,
  customization, and OpenTelemetry tracing with an OTLP exporter.
- Two Agent Skills, `xstructured` and `xstructured-extend`, with setup and
  contract checks, test templates, and evaluations.

### Changed

- The API is async first: the documentation, examples, and skills use
  `ainvoke`, `abatch`, and `astream`.
- `JsonSafetyError`, raised for duplicate keys, `NaN`, and overflowing
  numbers, is part of the public API.
- Dependencies require `langchain-core` 1.7.6 and `pydantic` 2.14.3 or
  newer.
- The documentation is built with Zensical, and its code blocks, links, and
  diagrams are checked in CI.

## [0.1.1] - 2026-10-04

### Added

- The `XStructuredError` hierarchy: `ParseError`, `EnvelopeError`,
  `SchemaError`, `LimitExceededError`, and `RecoveryError`, alongside
  `RepairError`.
- `ScanEvent` and `EnvelopeState` from the incremental `EnvelopeScanner`.
- `canonical_schema_json` and the `SchemaTarget` and `NamedSchemaTargets`
  types.
- `xstructured.__version__`.

### Changed

- Instructions are injected into strings, prompt values, and message-like
  sequences, with a clear `TypeError` for inputs that cannot carry them.
- Composition: downstream steps receive the final result whether a chain is
  invoked or streamed.
- Type inference: `StructuredParser(Model)` and
  `with_xstructured_output(runnable, Model)` infer the value type, including
  `list[Model]` for `multiple=True`.

### Security

- Limits are enforced in linear time.
- Exception messages never contain model output.

## [0.1.0] - 2026-09-19

The first release.

### Added

- `with_xstructured_output` and `XStructuredRunnable`: wrap any LangChain v1
  Runnable that returns text or messages, inject schema instructions, and
  return an `XStructuredResult` with the prose, the validated value, the raw
  output, and metadata.
- `StructuredParser`: envelope extraction, conservative recovery (Markdown
  fences and surrounding prose), strict JSON decoding, and Pydantic
  validation in JSON mode.
- Envelopes: `EnvelopeSpec`, the incremental `EnvelopeScanner`, and named
  envelopes such as `<xstructured name="finding">`.
- Multiple values: JSON arrays (`multiple=True`), named schemas with a
  `{"schema": ..., "payload": ...}` discriminator, and separately named
  envelopes (`multiple_envelopes=True`).
- Streaming: `StreamDecoder` and ordered `StreamEvent` values.
- Opt-in, bounded LLM-assisted repair with `RepairConfig`.
- Schema helpers: `inspect_schema`, `schema_instructions`,
  `fingerprint_schema`, and `inspect_named_schemas`.

### Security

- Input, envelope, payload, and nesting limits.
- Duplicate keys, `NaN`, `Infinity`, and overflowing numbers are rejected.

[Unreleased]: https://github.com/smuniharish/xstructured/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/smuniharish/xstructured/releases/tag/v1.0.0
[0.1.1]: https://pypi.org/project/xstructured/0.1.1/
[0.1.0]: https://pypi.org/project/xstructured/0.1.0/
