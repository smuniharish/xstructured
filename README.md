# xstructured

[![CI](https://github.com/smuniharish/xstructured/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/smuniharish/xstructured/actions/workflows/ci.yml)
[![Documentation](https://readthedocs.org/projects/xstructured/badge/?version=latest)](https://xstructured.readthedocs.io)
[![PyPI](https://img.shields.io/pypi/v/xstructured)](https://pypi.org/project/xstructured/)
[![Python 3.12 | 3.13 | 3.14](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)](https://github.com/smuniharish/xstructured/blob/master/pyproject.toml)
[![Coverage 100%](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/smuniharish/xstructured/blob/master/CONTRIBUTING.md#check-your-change)
[![Typed](https://img.shields.io/badge/typing-typed-blue)](https://peps.python.org/pep-0561/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](https://github.com/smuniharish/xstructured/blob/master/LICENSE)

**Validated Pydantic data _and_ natural-language text from one LLM response.**

`xstructured` wraps any LangChain v1 Runnable, chat model, or agent. The model answers in
its own words and places a JSON payload in an envelope; xstructured extracts it, validates
it with Pydantic v2, and returns both, even when the payload is wrapped in Markdown, buried
in prose, or still streaming in.

<p align="center">
  <img src="https://raw.githubusercontent.com/smuniharish/xstructured/master/docs/assets/diagrams/architecture-overview.png" alt="How a request flows through xstructured" width="596">
</p>

## Highlights

- **Validated, never guessed.** Strict JSON decoding and Pydantic validation in JSON mode.
  Recovery only selects which part of a response to parse; it never rewrites JSON.
- **Prose and data together.** `result.content` for people, `result.structured` for code.
- **Ordered streaming.** Text deltas as they arrive, and the validated value the moment its
  envelope closes.
- **A native Runnable.** `invoke`, `batch`, `stream`, async variants, tracing, retries,
  fallbacks, and composition behave as in any LangChain Runnable.
- **Bounded by design.** Input, envelope, payload, and nesting limits; duplicate keys,
  `NaN`, and overflowing numbers are rejected.
- **Optional, bounded repair.** An opt-in repair Runnable gets a fixed number of attempts,
  and its output must pass the same schema.
- **Fully typed.** The value type is inferred from your schema.

## Installation

```bash
pip install xstructured
```

Requires Python 3.12 or newer. The only runtime dependencies are `langchain-core` and
`pydantic`.

## Quickstart

```python
from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from xstructured import with_xstructured_output


class Contact(BaseModel):
    name: str
    email: str
    company: str | None = None


model = init_chat_model("openai:gpt-5-mini")
extractor = with_xstructured_output(model, Contact)
result = extractor.invoke(
    "Please loop in Priya Shah (priya.shah@example.com) from Acme Corp."
)

print(result.structured)  # Contact(name='Priya Shah', ...)
print(result.content)  # The model's prose, with the envelope removed.
```

Stream prose and data in order:

```python
from xstructured import StreamEventKind

message = "Add Priya Shah (priya.shah@example.com) to the review."
for event in extractor.stream(message):
    if event.kind is StreamEventKind.TEXT_DELTA:
        print(event.text, end="")
    elif event.kind is StreamEventKind.STRUCTURED_END:
        print("\nValidated:", event.structured)
```

Parse text from any source, without LangChain:

```python
from xstructured import StructuredParser

reply = (
    "Sure!\n"
    "```json\n"
    '{"name": "Priya Shah", "email": "priya.shah@example.com"}\n'
    "```"
)
result = StructuredParser(Contact).parse(reply)
print(result.value, result.recovered)  # Contact(...) True
```

Wrap chains, `create_agent` agents, Deep Agents, and LangGraph nodes too; see the
[integration guides](https://xstructured.readthedocs.io/en/latest/integrations/).

## Benchmarks

An offline benchmark runs 11 model-style outputs through four parsers and checks each
against an explicit expectation, counting a wrongly accepted truncated or ambiguous
payload as a failure:

| Mechanism | Correct | Median latency |
| --- | ---: | ---: |
| `json.loads` + Pydantic | 45.45% | 3.5 µs |
| LangChain `JsonOutputParser` + Pydantic | 45.45% | 284.0 µs |
| LangChain `PydanticOutputParser` | 45.45% | 249.7 µs |
| **xstructured** | **100%** | 21.0 µs |

Reproduce it with `uv run python -m benchmarks`; methodology and per-case results are in
the [benchmark documentation](https://xstructured.readthedocs.io/en/latest/benchmarks/).

## Examples

Nine [example scripts](https://github.com/smuniharish/xstructured/tree/master/examples)
cover single- and multi-agent extraction, Deep Agents, LangGraph routing, RAG citations,
incident analysis, streaming UIs, mixed payloads with repair, and named envelopes. Each
runs offline with a scripted model, or live against the Experiential Labs API when
`EXPLABS_API_KEY` is set.

## Documentation

Full documentation is at **[xstructured.readthedocs.io](https://xstructured.readthedocs.io)**:
[quickstart](https://xstructured.readthedocs.io/en/latest/getting-started/quickstart/),
[user guide](https://xstructured.readthedocs.io/en/latest/guide/),
[architecture](https://xstructured.readthedocs.io/en/latest/architecture/),
[security](https://xstructured.readthedocs.io/en/latest/security/), and the
[API reference](https://xstructured.readthedocs.io/en/latest/api/).

An [Agent Skill](https://github.com/smuniharish/xstructured/tree/master/skills/xstructured)
teaches AI coding agents to use xstructured correctly:

```bash
npx skills add smuniharish/xstructured --skill xstructured
```

## Contributing

Contributions are welcome. See
[CONTRIBUTING.md](https://github.com/smuniharish/xstructured/blob/master/CONTRIBUTING.md)
for the development workflow and
[SECURITY.md](https://github.com/smuniharish/xstructured/blob/master/SECURITY.md) for
reporting vulnerabilities.

## License

Licensed under the [Apache License 2.0](https://github.com/smuniharish/xstructured/blob/master/LICENSE).
