# Contributing

Thank you for improving xstructured. Contributions should keep its focus: a
small, dependable response contract for LangChain Runnables and agents, not an
agent framework, a provider SDK, or a prompt library.

Keep the core small. It depends only on `langchain-core` and `pydantic`;
everything else belongs in an optional extra. Every behavior a user can
replace is an abstract base class with a default and a contract suite in
`xstructured.testing`.

## Before opening a change

1. Read the [architecture overview](docs/architecture.md).
2. Open an issue first for changes to the public API, the envelope contract,
   the stream events, or an integration.
3. Keep each change focused, with tests and documentation for anything a user
   can observe.

## Development setup

Python 3.12 or later and [uv](https://docs.astral.sh/uv/) are required.

```bash
git clone https://github.com/smuniharish/xstructured.git
cd xstructured
uv sync --all-extras --all-groups
uv run ruff check .
uv run ruff format --check .
uv run pyrefly check
uv run coverage run -m pytest
uv run coverage report
```

- The default test run needs no services or API keys, and coverage is kept at
  **100%** of lines and branches.
- Warnings are errors in the test suite, so deprecated APIs are caught early.
- `HYPOTHESIS_PROFILE=ci` runs the property-based tests with more examples,
  as in CI.
- `uv run pytest -m live` runs the examples against the live Experiential
  Labs API; it needs `EXPLABS_API_KEY` and is never part of the default run.

Never commit credentials, local environments, or generated reports.

## Examples and benchmark

- Examples in [`examples/`](examples) are async and must run offline through
  the scripted model in `examples/_shared.py`. Add new ones to
  `tests/test_examples.py` with their expected output, and give each a page
  under [`docs/examples/`](docs/examples).
- Add parser edge cases to `benchmarks/cases.json` with an explicit expected
  value, or `null` when the input must be rejected, then run
  `uv run python -m benchmarks`.

## Agent Skills

The two skills live in [`xstructured-skills/skills/`](xstructured-skills/skills).
Keep them accurate when public behavior changes; `tests/skill` checks their
format, links, evaluations, scripts, and templates:

```bash
uv run pytest tests/skill
uvx --from skills-ref agentskills validate \
  xstructured-skills/skills/xstructured
uvx --from skills-ref agentskills validate \
  xstructured-skills/skills/xstructured-extend
```

The [validation guide](xstructured-skills/validation/README.md) describes how
to evaluate a change against real tasks.

## Documentation and diagrams

The documentation is built with [Zensical](https://zensical.org). Code blocks
are tested: every Python block must parse and use real APIs, pages that start
with `<!-- docs-test: run -->` are executed, and so are the examples in
docstrings. Code fits 80 columns; program output in `text` blocks wraps
instead.

```bash
uv sync --group docs --all-extras
uv run zensical serve
uv run zensical build --strict
uv run python scripts/check_site_links.py
```

Diagrams are Mermaid sources under [`diagrams/`](diagrams), rendered to PNG at
twice their size with Mermaid CLI 12.2.0. Install it globally; it needs
Node.js 22.13 or later. `--allow-scripts=puppeteer` lets Puppeteer download
the headless browser the CLI renders with:

```bash
npm install --global --allow-scripts=puppeteer @mermaid-js/mermaid-cli@12.2.0
node scripts/render-diagrams.mjs
node scripts/render-diagrams.mjs --check
```

Commit a changed diagram source together with its rendered image and the
updated `docs/assets/diagrams/manifest.json`, and embed it at half the PNG's
width (at most 656 pixels) so its text matches the page.

## Pull requests

- Describe the user-visible effect of the change.
- Add or update tests for every behavior change.
- Update the affected pages under [`docs/`](docs), the skills, and the
  [changelog](CHANGELOG.md).
- Make sure formatting, lint, type checks, tests, the strict docs build, and
  the diagram check pass.

## Releases

Releases follow [semantic versioning](https://semver.org/). To publish one:

1. Set the version in `pyproject.toml` and `metadata.version` in both Agent
   Skills, `xstructured-skills/skills/xstructured/SKILL.md` and
   `xstructured-skills/skills/xstructured-extend/SKILL.md`, then run
   `uv lock`. A test fails until the versions match.
2. Move the changelog entries under a heading with the version and date.
3. Merge to `master`, then publish a GitHub release whose tag is the version
   with a `v` prefix, such as `v1.0.0`.

The [release workflow](.github/workflows/release.yml) checks that the tag
matches the version, builds and checks the distributions, and publishes them
to PyPI with trusted publishing, so no API token is stored in the repository.
A maintainer adds the workflow as a trusted publisher in the PyPI project
settings (repository `smuniharish/xstructured`, workflow `release.yml`,
environment `pypi`).

## Security reports

Do not report vulnerabilities in public issues. Follow [SECURITY.md](SECURITY.md).
