# Contributing

Thank you for improving xstructured. Contributions should keep its focus: a small,
dependable response contract for LangChain Runnables, not an agent framework, a provider
SDK, or a prompt library. Please open an issue to discuss new public APIs or behavior
changes before sending a pull request.

## Set up

The project uses [uv](https://docs.astral.sh/uv/) and supports Python 3.12 to 3.14.

```bash
git clone https://github.com/smuniharish/xstructured.git
cd xstructured
uv sync
```

`uv sync` installs the package in editable mode with the test, lint, type-checking, and
example dependencies.

## Check your change

Run the same checks as continuous integration:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyrefly check
uv run pytest --cov
```

- Coverage must stay at **100%** of lines and branches.
- `HYPOTHESIS_PROFILE=ci` runs the property-based tests with more examples, as in CI.
- `uv run pytest -m live` runs the examples against the live Experiential Labs API; it
  needs `EXPLABS_API_KEY` and is never part of the default run.

Warnings are errors in the test suite, so deprecated APIs are caught early.

## Documentation

The documentation is built with MkDocs Material. Code blocks are tested: every Python
block must compile and use real APIs, pages that start with `<!-- docs-test: run -->`
are executed, and so are the examples in docstrings. Code in the documentation,
README, and examples fits 80 columns (Ruff formats it); program output in `text`
blocks wraps instead.

```bash
uv sync --group docs
uv run mkdocs serve
uv run mkdocs build --strict
```

Diagrams are Mermaid sources in
[`diagrams/`](https://github.com/smuniharish/xstructured/tree/master/diagrams), rendered to
PNG at twice their size with a pinned Mermaid CLI. Commit each source together with its
rendered image, and embed it at half the PNG's width (at most 656 pixels) so its text
matches the page:

```bash
npm ci --prefix scripts
node scripts/render-diagrams.mjs
node scripts/render-diagrams.mjs --check
```

## Examples, benchmark, and Agent Skill

- Examples in
  [`examples/`](https://github.com/smuniharish/xstructured/tree/master/examples) must run
  offline through the scripted model in `examples/_shared.py`; add new ones to
  `tests/test_examples.py` with their expected output.
- Add parser edge cases to `benchmarks/cases.json` with an explicit expected value, or
  `null` when the input must be rejected, then run `uv run python -m benchmarks`.
- Keep the Agent Skill in
  [`skills/xstructured/`](https://github.com/smuniharish/xstructured/tree/master/skills/xstructured)
  accurate when public behavior changes, and validate it with
  `uvx --from skills-ref agentskills validate skills/xstructured`.

## Pull requests

- Explain the user-visible effect of the change.
- Add tests for new behavior and update the documentation and the changelog.
- Make sure every check above passes.
