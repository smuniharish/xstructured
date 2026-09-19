# Contributing

Thank you for improving `xstructured`. Contributions should preserve its
narrow focus -- schema-guided structured output for `langchain-core`
`Runnable`s -- and avoid growing it into an agent framework, a provider SDK,
or a prompt-engineering library.

## Before opening a change

1. Read the [architecture overview](docs/architecture/overview.md).
2. Discuss material API changes (new public symbols, changed signatures, new
   required dependencies) in an issue first.
3. Keep a change focused; include tests and documentation for public
   behavior changes.

## Development

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run flake8 .
uv run pyrefly check
uv run pytest -m "not live"
```

Requires Python 3.11 or newer. Do not commit credentials, `.venv`,
`__pycache__`, or generated build output (see [.gitignore](.gitignore)).

`ruff` is pinned to `>=0.15,<0.16` in `pyproject.toml`: `ruff` 0.16.x panics
on this repository's `ruff format --check .` (an upstream renderer bug, not
a repository issue). Do not bump past `<0.16` without re-verifying against
a fixed release.

## Documentation and diagrams

Build the documentation with the docs dependency group:

```bash
uv sync --group docs
uv run mkdocs build --strict
```

Architecture diagrams are Mermaid source files under [`diagrams/`](diagrams).
Render their PNG counterparts (committed under
[`docs/assets/diagrams/`](docs/assets/diagrams)) with:

```bash
npm install --global @mermaid-js/mermaid-cli@11.17.0
node scripts/render-diagrams.mjs
node scripts/render-diagrams.mjs --check
```

Commit a changed Mermaid source and its re-rendered PNG together; CI
(`.github/workflows/docs.yml`) fails if they drift.

## Offline parser benchmark

Run the checked-in correctness and timing experiment without credentials or
network access:

```bash
uv run python -m benchmarks --help
uv run python -m benchmarks --iterations 100
```

The methodology and publication requirements are in
[`docs/benchmarks.md`](docs/benchmarks.md). Update
[`benchmarks/cases.json`](benchmarks/cases.json) when adding a new parser edge
case, and keep its expected acceptance outcome explicit.

## Examples

Scripts under [`examples/`](examples) must stay importable and smoke-testable
without any API key or optional package installed --
[`tests/test_examples_smoke.py`](tests/test_examples_smoke.py) enforces this
in CI. If you add an example, gate it with `require_env` / `require_package`
from [`examples/_shared.py`](examples/_shared.py) and add it to
[`examples/README.md`](examples/README.md) and
[`docs/examples/index.md`](docs/examples/index.md).

## Pull request expectations

- Explain the user-visible and architectural impact.
- Add or update tests for behavior changes.
- Update relevant user-facing pages under [`docs/`](docs).
- Ensure format, lint, types, tests, diagram rendering, and the strict docs
  build all pass.
