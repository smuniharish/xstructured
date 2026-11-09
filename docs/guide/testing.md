# Testing

`xstructured.testing` helps you test code that uses xstructured without a model
provider, and check your own [extension points](extension-points.md). It
depends only on `langchain-core` and is safe to import from test suites.

## Scripted chat model

`ScriptedChatModel` is a LangChain chat model that replays the responses you
give it, one per call, as strings or `AIMessage` values. It supports
`ainvoke`, `astream` (one chunk per word), and `bind_tools`, so it works with
`with_xstructured_output`, `XStructuredOutputParser` chains, `create_agent`,
and `create_deep_agent`.

```python
import pytest
from pydantic import BaseModel

from xstructured import ParseError, with_xstructured_output
from xstructured.testing import ScriptedChatModel


class Ticket(BaseModel):
    queue: str
    urgent: bool


async def test_routes_billing_questions() -> None:
    model = ScriptedChatModel.of(
        "Billing handles refunds. <xstructured>"
        '{"queue": "billing", "urgent": false}</xstructured>'
    )
    router = with_xstructured_output(model, Ticket)

    result = await router.ainvoke("I was charged twice.")

    assert result.structured == Ticket(queue="billing", urgent=False)
    assert result.content == "Billing handles refunds. "


async def test_reports_the_failing_response() -> None:
    model = ScriptedChatModel.of("I am not sure where this goes.")
    router = with_xstructured_output(model, Ticket)

    with pytest.raises(ParseError) as caught:
        await router.ainvoke("Hello?")

    assert caught.value.text == "I am not sure where this goes."
```

Tool calls are scripted as `AIMessage(content="", tool_calls=[...])`, followed
by the final answer, to test an agent's tool loop.

## Contract tests

Each extension point has a contract test suite. Subclass it in a test module,
implement its `make_*` methods, and pytest runs every check against your
implementation:

| Suite | Implement |
| --- | --- |
| `JsonDecoderContract` | `make_decoder()` |
| `RecoveryStrategyContract` | `make_strategy()`; optionally `sample_texts()` |
| `InstructionInjectorContract` | `make_injector()`, `make_input()` |
| `OutputTextExtractorContract` | `make_extractor()`, `make_output(text)`, `make_chunks(text)` |
| `ObserverContract` | `make_observer()` |

```python
from xstructured import JsonDecoder, Observer, StrictJsonDecoder
from xstructured.testing import JsonDecoderContract, ObserverContract

from myapp.telemetry import MetricsObserver


class TestStrictDecoder(JsonDecoderContract):
    def make_decoder(self) -> JsonDecoder:
        return StrictJsonDecoder()


class TestMetricsObserver(ObserverContract):
    def make_observer(self) -> Observer:
        return MetricsObserver()
```

The suites check the behavior the parser relies on, for example that a decoder
raises `ValueError` for invalid JSON and documents nested too deeply, that a
recovery strategy yields the text as given first, or that an injector returns
a new value without modifying its input.

## Live tests

xstructured's own live suite runs the examples against a real provider:

```bash
EXPLABS_API_KEY="your-key" uv run pytest -m live
```

Keep keys in your environment, never in code or configuration files.
