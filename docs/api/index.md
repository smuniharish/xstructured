# API reference

Everything below is importable from the top-level package, for example
`from xstructured import with_xstructured_output`.

| Area | Symbols |
| --- | --- |
| [Runnable integration](runnable.md) | `with_xstructured_output`, `XStructuredRunnable` |
| [Parsing](parsing.md) | `StructuredParser` |
| [Envelopes](envelopes.md) | `EnvelopeSpec`, `EnvelopeScanner`, `EnvelopeState`, `ScanEvent` |
| [Schemas](schemas.md) | `inspect_schema`, `SchemaInfo`, `SchemaTarget`, `schema_instructions`, `fingerprint_schema`, `canonical_schema_json`, `inspect_named_schemas`, `NamedSchemas`, `NamedSchemaSpec`, `NamedSchemaTargets` |
| [Streaming](streaming.md) | `StreamDecoder`, `StreamEvent`, `StreamEventKind` |
| [Configuration](configuration.md) | `ParserConfig`, `RecoveryConfig`, `RepairConfig` |
| [Results](results.md) | `XStructuredResult`, `ParseResult` |
| [Errors](errors.md) | `XStructuredError`, `SchemaError`, `EnvelopeError`, `ParseError`, `LimitExceededError`, `RecoveryError`, `RepairError` |

`xstructured.__version__` holds the installed version.
