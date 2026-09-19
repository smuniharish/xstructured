# Parsing and recovery

`StructuredParser` validates text against a Pydantic v2 schema target,
optionally extracting an [envelope](envelope.md) first:

```python
from pydantic import BaseModel
from xstructured import StructuredParser


class Answer(BaseModel):
    value: int


parser = StructuredParser(Answer)
result = parser.parse('{"value": 42}')
assert result.value == Answer(value=42)
assert not result.recovered
```

## Recovery candidates

When `ParserConfig().recovery.enabled` (the default), the parser tries a
small, ordered list of *conservative* candidates before giving up -- it
never rewrites JSON syntax (no quote-fixing, no trailing-comma removal), it
only changes which substring of the response is treated as the payload:

1. the text as given;
2. the body of a single ```` ```json ... ``` ```` fence, if present;
3. the substring between the first `{`/`[` and the last matching `}`/`]`.

```python
result = parser.parse("Here you go:\n```json\n{\"value\": 5}\n```\n")
assert result.value.value == 5
assert result.recovered
```

If every candidate fails, a `RecoveryError` (a `ParseError` subclass) is
raised with the attempted candidates and the underlying validation errors
attached, so the failure is debuggable rather than a bare JSON error.

Runnable results also include operational metadata for tracing and
cost/quality analysis: `envelope_detected`, `envelope_count`, `parse_duration`,
`validation_duration`, `repair_attempted`, `repair_attempt_count`, and
`stream_completed`, alongside the schema fingerprint and provider usage
metadata when LangChain supplies it.

See [Repair and recovery](repair.md) for the full failure policy and
[Multiple payloads](multiple-payloads.md) for ambiguous-output behavior.

## Requiring an envelope

`ParserConfig(require_envelope=True)`, or passing an `envelope=` to
`StructuredParser`, makes a missing or incomplete envelope a `ParseError`
instead of silently falling back to parsing the whole input. The
[LangChain integration](../integrations/langchain.md) always requires an
envelope, since it also injects the matching instructions.
