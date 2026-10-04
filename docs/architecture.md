# Architecture

![Architecture overview](assets/diagrams/architecture-overview.png){ .diagram width="596" }

## Components

| Component | Module | Responsibility |
| --- | --- | --- |
| `XStructuredRunnable` | `xstructured.langchain` | Adds instructions, runs the wrapped Runnable as a traced child run, parses, optionally repairs, and builds results. |
| `StructuredParser` | `xstructured.parser` | Envelope extraction, conservative recovery, strict JSON, Pydantic validation. |
| `EnvelopeScanner`, `EnvelopeSpec` | `xstructured.envelope` | Incremental, JSON-aware envelope detection. |
| `StreamDecoder` | `xstructured.streaming` | Maps scanner output to ordered `StreamEvent` values; validates on close. |
| Schema helpers | `xstructured.schema` | Introspection, instructions, named schemas, fingerprints. |
| Configuration, results, errors | `xstructured.core` | Frozen configuration models, result types, the exception hierarchy. |

Everything you need is exported from the top-level `xstructured` package.

## Request lifecycle

![Request lifecycle](assets/diagrams/request-lifecycle.png){ .diagram width="653" }

1. The input is normalized and the schema instructions are added.
2. The wrapped Runnable runs as a child run with the same configuration (callbacks,
   tags, metadata, and recursion limits).
3. The parser locates the envelope, tries recovery candidates in order, decodes strict
   JSON, and validates in Pydantic's JSON mode.
4. If validation fails and repair is configured, the repair Runnable is asked for a
   corrected response, at most `max_attempts` times, and every response is validated by
   the same parser.
5. The result combines the prose, the validated value, the raw output, and metadata.

Streaming follows the same steps incrementally: the
[stream decoder](guide/streaming.md) validates the payload once, when its envelope closes,
and the final `RESULT` event matches what `invoke` would return.

## Design principles

**Validation is the authority.** Recovery only selects a substring of the response and
repair only replaces it; neither ever relaxes the schema.

**Linear, bounded work.** Envelope scanning, string tracking, and nesting checks run as
single compiled-regex passes whose cost grows linearly with input size, and every stage
enforces a configured limit.

**One parse per response.** The schema is introspected once per wrapper, and a streamed
payload is validated exactly once.

**Native LangChain behavior.** The wrapper is a standard Runnable: it is traced, it
composes, and inside a chain it emits the same value whether the chain is invoked or
streamed.

**Explicit failures.** Every failure is a typed `ParseError` subclass carrying the
offending text, and configuration mistakes fail when the parser or wrapper is created.
