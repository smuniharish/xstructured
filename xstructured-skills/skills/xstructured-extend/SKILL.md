---
name: xstructured-extend
description: >-
  Use this skill when customizing how xstructured parses, prompts, or reports:
  writing a JsonDecoder, RecoveryStrategy, InstructionRenderer,
  InstructionInjector, OutputTextExtractor, RepairPromptBuilder, or Observer
  subclass, for example a lenient decoder, a strategy for a model's quirky
  output, instructions in another language, input or output shapes the
  defaults reject, or metrics sent to Prometheus, StatsD, or Datadog. Also use
  it to test such a subclass with the xstructured.testing contract suites or
  check_extension.py, and to debug a failing contract test. Do not use it to
  add xstructured to an application, wire agents or LangGraph, configure
  limits or repair, or turn on OpenTelemetry; the xstructured skill covers
  those.
license: Apache-2.0
compatibility: >-
  Python 3.12 or newer with xstructured 1.x installed (pip install
  xstructured). The templates and scripts run offline and need no model
  credentials.
metadata:
  version: "1.0.0"
  documentation: "https://xstructured.readthedocs.io/en/latest/guide/extension-points/"
---

# Extending xstructured

Every behavior of xstructured is an abstract base class with a default:
`InstructionRenderer`, `InstructionInjector`, `OutputTextExtractor`,
`RecoveryStrategy`, `JsonDecoder`, `RepairPromptBuilder`, and `Observer`.
Subclass one, implement its abstract methods, and pass an instance with the
matching keyword (`decoder=`, `recovery=`, `observer=`, ...). Five of them
have a contract suite in `xstructured.testing` that tests every promise.

Before writing a subclass, check whether configuration already does it:

| Need | Configure instead |
| --- | --- |
| Different delimiters | `envelope=EnvelopeSpec(...)` |
| Fewer recovery candidates or none | `ParserConfig(recovery=RecoveryConfig(...))` |
| Strict or forbidding validation, a validation context | `schema_options=SchemaOptions(...)` |
| Another state key, or only some LangGraph nodes | `MessageTextExtractor(messages_key=..., nodes=...)` |
| Instructions in your own prompt | `inject_instructions=False` and `.instructions` |
| OpenTelemetry spans | `xstructured.otel.OpenTelemetryObserver` |

## Workflow: a decoder or a recovery strategy

1. Copy `assets/decoder_template.py`. Keep the rules in its comments: a
   decoder raises `ValueError` for text it rejects and keeps the
   `StrictJsonDecoder` safety rules; a strategy yields the stripped text
   first and only distinct, non-empty substrings.
2. Copy `assets/test_extensions.py` and keep the contract classes for what
   you wrote: `JsonDecoderContract`, `RecoveryStrategyContract`.
3. Run the tests, or `python scripts/check_extension.py module:Factory`
   from the project root. Fix the first broken promise and rerun until all
   hold. Read [references/extension-points.md](references/extension-points.md)
   when a promise is unclear.
4. Pass it in: `with_xstructured_output(model, Schema, decoder=...)`, and
   add an end-to-end test with `ScriptedChatModel` replaying a reply the
   default rejects.

## Workflow: an observer

1. Copy `assets/observer_template.py` and replace its `_record_*` methods
   with calls to the metrics backend.
2. Keep `ObserverContract` from `assets/test_extensions.py`, plus an
   end-to-end test that asserts what the backend received.
3. Run `python scripts/check_extension.py module:Factory`, then pass
   `observer=` to every wrapper and middleware. Read
   [references/observers.md](references/observers.md) for the lifecycle and
   attributes.

## Workflow: injector, extractor, renderer, or repair prompt

1. Read the signature and promises in
   [references/extension-points.md](references/extension-points.md).
2. Subclass the default when you only change part of its behavior
   (`DefaultInstructionRenderer`, `MessageTextExtractor`,
   `MessageInstructionInjector`, `DefaultRepairPrompt`).
3. Test injectors with `InstructionInjectorContract` and extractors with
   `OutputTextExtractorContract` (both need sample inputs, so pytest only).
   Renderers and repair prompts have no contract: test their output with
   `ScriptedChatModel`.

## Checklist before you finish

- [ ] The class subclasses the matching ABC; constructors reject anything else.
- [ ] Every contract test for it passes, and so does an end-to-end test.
- [ ] No blocking I/O on the event loop; no prompt or response text in telemetry.
- [ ] The project's own tests pass.

## Gotchas

- **Never loosen safety.** A decoder must not accept `NaN`, duplicate keys,
  or nesting deeper than `max_nesting_depth`. A strategy must never rewrite
  JSON; return substrings only.
- A decoder that raises something other than `ValueError` for bad text fails
  the whole call instead of trying the next candidate.
- `json_text` must return standard JSON: Pydantic validates it in JSON mode,
  so strict models keep accepting ISO dates and similar.
- Extension points are synchronous on purpose; do not make them async.
- `fail` also receives cancellations; do not report them as errors.
- An observation is finished exactly once; guard against double calls and
  never raise from it.
- Changing the renderer changes what models produce. Re-run live checks.

## Files

- `assets/decoder_template.py`: `PythonLiteralDecoder` and `LastLineFirst`
  to copy.
- `assets/observer_template.py`: `MetricsObserver` to point at a backend.
- `assets/test_extensions.py`: the contract classes and end-to-end tests
  both templates pass.
- `scripts/check_extension.py`: runs the contract for a decoder, strategy, or
  observer factory without pytest. Run `--help` for options; `--json` prints
  one object. Exit codes are 0 (all hold), 1 (a promise broken), and 2
  (factory not loadable or unsupported).
- [references/extension-points.md](references/extension-points.md): every
  base class, its keyword, signature, promises, and contract.
- [references/observers.md](references/observers.md): lifecycle, attributes,
  and rules for observers.
