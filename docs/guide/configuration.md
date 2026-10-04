<!-- docs-test: run -->

# Configuration and limits

All parsing behavior is controlled by three immutable Pydantic models.

## ParserConfig

| Field | Default | Purpose |
| --- | --- | --- |
| `max_input_chars` | 1,000,000 | Longest accepted response (or whole stream). |
| `max_envelope_chars` | 1,000,000 | Longest envelope, delimiters included. |
| `max_payload_chars` | 1,000,000 | Longest JSON payload. |
| `max_nesting_depth` | 100 (at most 1,000) | Deepest JSON array or object nesting. |
| `recovery` | `RecoveryConfig()` | Conservative recovery settings. |
| `require_envelope` | `False` | Fail when no complete envelope is present. |

Exceeding the input, envelope, or payload-in-envelope limit raises `LimitExceededError`
immediately. A recovery candidate that is too long or too deep only fails that candidate.

```python
from pydantic import BaseModel

from xstructured import LimitExceededError, ParserConfig, StructuredParser


class Event(BaseModel):
    name: str


parser = StructuredParser(
    Event,
    config=ParserConfig(
        max_input_chars=10_000,
        max_envelope_chars=5_000,
        max_payload_chars=4_000,
        max_nesting_depth=16,
    ),
)

try:
    parser.parse("x" * 20_000)
except LimitExceededError as error:
    assert error.limit == "max_input_chars"
    assert error.maximum == 10_000
```

`with_xstructured_output(..., parser_config=...)` uses the same configuration; the wrapper
always requires an envelope.

## RecoveryConfig

| Field | Default | Purpose |
| --- | --- | --- |
| `enabled` | `True` | Try recovery candidates when the text as given fails. |
| `strip_markdown_fences` | `True` | Try the body of a fence that wraps the whole text. |
| `strip_surrounding_text` | `True` | Try the outermost object or array substring. |
| `max_candidates` | 4 | Number of candidates to try, including the text as given. |

```python
from xstructured import ParseError, RecoveryConfig

exact = StructuredParser(
    Event, config=ParserConfig(recovery=RecoveryConfig(enabled=False))
)

try:
    exact.parse('Sure: {"name": "deploy"}')
except ParseError as error:
    print(error)  # Invalid JSON: Expecting value: line 1 column 1 (char 0)
```

## RepairConfig

| Field | Default | Purpose |
| --- | --- | --- |
| `enabled` | `True` | Allow the configured repair Runnable to run. |
| `max_attempts` | 1 (at most 5) | Repair calls per response. |

`RepairConfig` only matters when a `repair` Runnable is passed; see
[Bounded repair](repair.md).

## Choosing limits

The defaults suit most chat responses. Tighten them for services that accept input from
untrusted users, and size them a little above your largest legitimate response:

- Keep `max_input_chars` close to the provider's maximum output for your model.
- Set `max_payload_chars` from your schema: a short form needs kilobytes, not megabytes.
- Keep `max_nesting_depth` low; real schemas rarely nest more than ten levels.

All configuration objects are frozen and reject unknown fields, so a typo fails at
construction instead of silently using a default.
