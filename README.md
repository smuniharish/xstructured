# xstructured

[![CI](https://github.com/xstructured/xstructured/actions/workflows/ci.yml/badge.svg)](https://github.com/xstructured/xstructured/actions/workflows/ci.yml)
[![Docs](https://github.com/xstructured/xstructured/actions/workflows/docs.yml/badge.svg)](https://xstructured.readthedocs.io)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

`xstructured` is a schema-guided structured output layer for
[LangChain v1](https://docs.langchain.com/oss/python/releases/langchain-v1)
`Runnable`s and agents. It wraps any chat model, `create_agent` agent, or
custom `Runnable` so that its natural-language output is turned into a
validated [Pydantic v2](https://docs.pydantic.dev/latest/) object, with
conservative recovery from markdown fences and surrounding prose, an
optional delimited envelope protocol for reliable extraction alongside
free-form text, and ordered streaming of text and structured deltas.

It is not a replacement for `create_agent`'s built-in `output_schema` and
does not call an LLM provider itself: it composes with whatever `Runnable`
you already have, focuses on making structured extraction robust to
imperfect model output, and stays out of the way otherwise.

## Installation

```bash
pip install xstructured
```

The Python import namespace is:

```python
from xstructured import with_xstructured_output, XStructuredResult
```

Running the examples against a real LLM provider additionally requires the
`examples` dependency group (LangChain, an OpenAI chat model, and optionally
Deep Agents):

```bash
uv sync --group examples
```

## Quickstart

```python
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

from xstructured import with_xstructured_output


class ContactInfo(BaseModel):
    name: str
    email: str


agent = create_agent(model="openai:gpt-4o-mini", tools=[])


def run_agent(messages):
    # create_agent's compiled graph takes/returns a {"messages": [...]} state,
    # so it is adapted to the plain-message Runnable contract xstructured expects.
    state = agent.invoke({"messages": list(messages)})
    return state["messages"][-1]


extractor = with_xstructured_output(RunnableLambda(run_agent), ContactInfo)

result = extractor.invoke(
    [HumanMessage(content="Reach Priya Shah at priya.shah@example.com.")]
)

print(result.structured)  # ContactInfo(name='Priya Shah', email='priya.shah@example.com')
print(result.content)     # the agent's natural-language reply, envelope stripped
print(result.raw)         # the original AIMessage
```

See [Why xstructured?](docs/integrations/why-xstructured.md) for ten practical
use cases and guidance on when LangChain or LangGraph native features are the
better choice.

`with_xstructured_output` composes with `.invoke`, `.ainvoke`, `.batch`,
`.abatch`, `.stream`, and `.astream`, following native `Runnable` semantics
throughout. Streaming yields ordered `TEXT_DELTA`, `STRUCTURED_START`,
`STRUCTURED_DELTA`, `STRUCTURED_END`, and `RESULT` events so a UI can render
prose and structured data as they arrive.

Lower-level building blocks are also public, for callers who want schema
instructions, parsing, or fingerprinting without the `Runnable` wrapper:

```python
from xstructured import StructuredParser, fingerprint_schema, schema_instructions

instructions = schema_instructions(ContactInfo, envelope="xstructured")
result = StructuredParser(ContactInfo).parse(model_output_text)
digest = fingerprint_schema(ContactInfo)
```

## Offline benchmark

Compare plain JSON plus Pydantic, LangChain's JSON and Pydantic output
parsers, and `xstructured` against the same local fixture corpus:

```bash
uv run python -m benchmarks --help
uv run python -m benchmarks
```

The benchmark performs no network calls and needs no API key. Its correctness
criteria, corpus, and timing methodology are documented in
[`docs/benchmarks.md`](docs/benchmarks.md).

## Resource limits and strict JSON

`ParserConfig` bounds all untrusted response handling. Its defaults limit
whole inputs, envelopes, and JSON payloads to 1,000,000 characters and JSON
container nesting to 100 levels. The same configuration is used by
`StructuredParser` and streaming wrappers.

```python
from xstructured import ParserConfig, StructuredParser

parser = StructuredParser(
    ContactInfo,
    config=ParserConfig(
        max_input_chars=100_000,
        max_envelope_chars=50_000,
        max_payload_chars=40_000,
        max_nesting_depth=32,
    ),
)
```

JSON decoding rejects duplicate object keys and non-standard `NaN`,
`Infinity`, and `-Infinity` constants. Envelopes that are incomplete or
exceed their configured bounds fail explicitly rather than continuing to
accumulate streamed content.

## Examples

Runnable, environment-gated example scripts live in [`examples/`](examples/):

- [`examples/single_agent_extraction.py`](examples/single_agent_extraction.py) â€”
  one `create_agent` agent wrapped with `with_xstructured_output`.
- [`examples/multi_agent_pipeline.py`](examples/multi_agent_pipeline.py) â€”
  an extractor agent feeding a reviewer agent, each schema-validated.
- [`examples/deep_agent_optional.py`](examples/deep_agent_optional.py) â€”
  the same pattern applied to a `deepagents` deep agent, skipped
  automatically when `deepagents` is not installed.

Each script checks for `EXPLABS_API_KEY` and prints an explanation and exits
instead of failing when it is not set,
so they are safe to run in any environment. See
[`examples/README.md`](examples/README.md) for details.

## Documentation

Full documentation, including user guides, architecture, security, benchmarks,
and API reference, is
published at <https://xstructured.readthedocs.io> and built from
[`docs/`](docs/) with MkDocs Material.

## Development

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run flake8 .
uv run pyrefly check
uv run pytest -m "not live"
```

Documentation diagrams are Mermaid sources rendered to PNG with a pinned
Mermaid CLI (see [`scripts/render-diagrams.mjs`](scripts/render-diagrams.mjs)):

```bash
# Install this tooling globally; the Python package has no Node runtime dependency.
npm install --global @mermaid-js/mermaid-cli@11.17.0
node scripts/render-diagrams.mjs
node scripts/render-diagrams.mjs --check
```

`node_modules/` is not required in the repository. The renderer uses a local
CLI when present and otherwise resolves the pinned global Mermaid CLI.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow.

The project requires Python 3.12 or newer and is licensed under
[Apache-2.0](LICENSE).
