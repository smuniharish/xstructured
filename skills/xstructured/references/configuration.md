# Configuration

## ParserConfig

| Field | Default | Notes |
| --- | --- | --- |
| `max_input_chars` | 1,000,000 | Whole response or stream; exceeding it raises `LimitExceededError`. |
| `max_envelope_chars` | 1,000,000 | One envelope, delimiters included. |
| `max_payload_chars` | 1,000,000 | One JSON payload. |
| `max_nesting_depth` | 100 | At most 1,000. |
| `recovery` | `RecoveryConfig()` | See below. |
| `require_envelope` | `False` | The wrapper always sets it to `True`. |

```python
from xstructured import ParserConfig, StructuredParser

config = ParserConfig(
    max_input_chars=20_000,
    max_payload_chars=8_000,
    max_nesting_depth=16,
)
parser = StructuredParser(dict, config=config)
```

Size limits close to the largest legitimate response; never raise them to make failures
go away.

## RecoveryConfig

Candidates, in order: the text as given, a Markdown fence that wraps the whole text, the
outermost `{...}`, the outermost `[...]`. Recovery never edits JSON.

| Field | Default |
| --- | --- |
| `enabled` | `True` |
| `strip_markdown_fences` | `True` |
| `strip_surrounding_text` | `True` |
| `max_candidates` | 4 (1-4) |

## RepairConfig

Repair runs only when `repair=` is passed, after parsing and recovery fail, and never for
`LimitExceededError`. Each attempt is validated by the same parser.

| Field | Default |
| --- | --- |
| `enabled` | `True` |
| `max_attempts` | 1 (1-5) |

```python
from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from xstructured import RepairConfig, with_xstructured_output


class Invoice(BaseModel):
    number: str
    total: float


model = init_chat_model("openai:gpt-5-mini")
invoices = with_xstructured_output(
    model, Invoice, repair=model, repair_config=RepairConfig(max_attempts=2)
)
```

`result.repaired` and `result.repair_attempts` report whether repair was used.

## Strictness that always applies

Duplicate keys, `NaN` and `Infinity`, and numbers that overflow to infinity are rejected.
Validation uses Pydantic's JSON mode, so strict models accept ISO dates and similar JSON
representations.
