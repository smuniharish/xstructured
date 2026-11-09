# API reference

The core API is importable from the top-level package, for example
`from xstructured import with_xstructured_output`. The agent middleware,
OpenTelemetry, and testing helpers live in submodules, so `import xstructured`
does not need their optional dependencies.

| Area | Symbols |
| --- | --- |
| [Runnable integration](runnable.md) | `with_xstructured_output`, `XStructuredRunnable`, `CONTEXT_KEY` |
| [Agent middleware](agents.md) | `xstructured.agents.XStructuredMiddleware` |
| [Output parser](output-parser.md) | `XStructuredOutputParser` |
| [Parsing](parsing.md) | `StructuredParser` |
| [Envelopes](envelopes.md) | `EnvelopeSpec`, `EnvelopeScanner`, `EnvelopeState`, `ScanEvent` |
| [Schemas](schemas.md) | `inspect_schema`, `SchemaInfo`, `SchemaTarget`, `schema_instructions`, `fingerprint_schema`, `canonical_schema_json`, `inspect_named_schemas`, `NamedSchemas`, `NamedSchemaSpec`, `NamedSchemaTargets` |
| [Streaming](streaming.md) | `StreamDecoder`, `StreamEvent`, `StreamEventKind` |
| [Configuration](configuration.md) | `ParserConfig`, `RecoveryConfig`, `RepairConfig`, `SchemaOptions` |
| [Extension points](contracts.md) | `InstructionRenderer`, `InstructionInjector`, `OutputTextExtractor`, `RecoveryStrategy`, `JsonDecoder`, `RepairPromptBuilder`, and their defaults |
| [Observability](observability.md) | `Observer`, `Observation`, `AttributeValue`, `xstructured.otel.OpenTelemetryObserver` |
| [Results](results.md) | `XStructuredResult`, `ParseResult` |
| [Errors](errors.md) | `XStructuredError`, `SchemaError`, `EnvelopeError`, `ParseError`, `LimitExceededError`, `JsonSafetyError`, `RecoveryError`, `RepairError` |
| [Testing](testing.md) | `xstructured.testing.ScriptedChatModel` and the contract test suites |

`xstructured.__version__` holds the installed version.
