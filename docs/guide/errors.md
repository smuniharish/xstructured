<!-- docs-test: run -->

# Error handling

Every exception raised by xstructured derives from `XStructuredError`. Failures caused by
model output derive from `ParseError`.

```text
XStructuredError
├── SchemaError           schema target cannot be used, or named schemas are invalid
├── EnvelopeError         invalid envelope delimiters or names
└── ParseError            the response could not be turned into a valid value
    ├── LimitExceededError    a resource limit was exceeded (never repaired)
    ├── RecoveryError         no recovery candidate produced a valid value
    └── RepairError           opt-in repair did not produce a valid response
```

`SchemaError` and `EnvelopeError` signal configuration mistakes and are raised when you
create a parser or wrapper. Invalid option combinations raise `ValueError`.

## What a ParseError carries

| Attribute | Available on | Meaning |
| --- | --- | --- |
| `text` | every `ParseError` | The model output that failed. Never part of `str(error)`. |
| `limit`, `maximum` | `LimitExceededError` | Which `ParserConfig` limit was exceeded, and its value. |
| `failures` | `RecoveryError` | One failure description per candidate tried. |
| `attempts`, `failures` | `RepairError` | Repair calls made, one failure per attempt. |

Keeping the response out of the message means logging an error does not leak model
output. All exceptions can be pickled, so they cross process boundaries intact.

```python
import pickle

from pydantic import BaseModel

from xstructured import ParseError, RecoveryError, StructuredParser


class Answer(BaseModel):
    value: int


try:
    StructuredParser(Answer).parse('{"value": "secret-ish model output"}')
except RecoveryError as error:
    assert "secret-ish" not in str(error)
    assert error.text == '{"value": "secret-ish model output"}'
    restored = pickle.loads(pickle.dumps(error))
    assert restored.failures == error.failures
```

## Handling failures in an application

```python
from xstructured import LimitExceededError


def extract(parser: StructuredParser[Answer], text: str) -> Answer | None:
    try:
        return parser.parse(text).value
    except LimitExceededError:
        return None  # Oversized: reject without retrying.
    except ParseError as error:
        # Log the reason; keep error.text internal.
        print(f"invalid response: {error}")
        return None


assert extract(StructuredParser(Answer), '{"value": 1}') == Answer(value=1)
assert extract(StructuredParser(Answer), "no JSON here") is None
```

With the LangChain wrapper, the same exceptions propagate from `invoke`, `ainvoke`,
`stream`, and `astream`. Combine them with LangChain's own resilience tools, for example
`wrapper.with_retry(retry_if_exception_type=(RecoveryError,))` to resample the model, or
`wrapper.with_fallbacks([...])` to try another model.
