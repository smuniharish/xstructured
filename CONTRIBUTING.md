# Contributing

Thank you for improving xstructured. Contributions should keep its focus: a
small, dependable response contract for LangChain Runnables and agents, not an
agent framework, a provider SDK, or a prompt library.

Keep the core small. It depends only on `langchain-core` and `pydantic`;
everything else belongs in an optional extra. Every behavior a user can
replace is an abstract base class with a default and a contract suite in
`xstructured.testing`.

## Before opening a change

1. Read the [architecture overview](https://github.com/smuniharish/xstructured/blob/master/docs/architecture.md).
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

- Examples in [`examples/`](https://github.com/smuniharish/xstructured/tree/master/examples) are async and must run offline through
  the scripted model in `examples/_shared.py`. Add new ones to
  `tests/test_examples.py` with their expected output, and give each a page
  under [`docs/examples/`](https://github.com/smuniharish/xstructured/tree/master/docs/examples).
- Add parser edge cases to `benchmarks/cases.json` with an explicit expected
  value, or `null` when the input must be rejected, then run
  `uv run python -m benchmarks`.

## Agent Skills

The two skills live in [`xstructured-skills/skills/`](https://github.com/smuniharish/xstructured/tree/master/xstructured-skills/skills).
Keep them accurate when public behavior changes; `tests/skill` checks their
format, links, evaluations, scripts, and templates:

```bash
uv run pytest tests/skill
uvx --from skills-ref agentskills validate \
  xstructured-skills/skills/xstructured
uvx --from skills-ref agentskills validate \
  xstructured-skills/skills/xstructured-extend
```

The [validation guide](https://github.com/smuniharish/xstructured/blob/master/xstructured-skills/validation/README.md) describes how
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

Diagrams are Mermaid sources under [`diagrams/`](https://github.com/smuniharish/xstructured/tree/master/diagrams), rendered to PNG at
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
- Update the affected pages under [`docs/`](https://github.com/smuniharish/xstructured/tree/master/docs), the skills, and the
  [changelog](https://github.com/smuniharish/xstructured/blob/master/CHANGELOG.md).
- Make sure formatting, lint, type checks, tests, the strict docs build, and
  the diagram check pass.

## Releases

Releases follow [semantic versioning](https://semver.org/) and are performed
manually by a maintainer. CI does not publish packages or create releases.

1. Set the version in `pyproject.toml` and `metadata.version` in both Agent
   Skills, then run `uv lock`. Move the changelog entries under a heading with
   the version and release date.
2. Review and merge the release changes, and confirm the normal CI checks.
3. Build the wheel and source distribution into an empty release directory:

   ```bash
   uv build --out-dir dist/release
   uvx twine check --strict dist/release/*
   ```

4. Inspect the distribution names and metadata. For example, the following
   prints the wheel's metadata; inspect the source archive as well:

   ```bash
   python -c "import glob, zipfile; \
   p = glob.glob('dist/release/*.whl'); assert len(p) == 1; \
   z = zipfile.ZipFile(p[0]); \
   n = next(n for n in z.namelist() if n.endswith('.dist-info/METADATA')); \
   print(z.read(n).decode())"
   tar -tf dist/release/*.tar.gz
   ```

5. After reviewing the artifacts, publish them **manually** using a securely
   configured PyPI credential. See the
   [`uv publish` guide](https://docs.astral.sh/uv/guides/package/#publishing-your-package)
   for authentication; do not commit credentials.

   ```bash
   uv publish dist/release/*
   ```
6. Create the GitHub release and its `v`-prefixed tag manually, using the
   reviewed changelog. Do not configure automated PyPI publishing.

## Security reports

Do not report vulnerabilities in public issues. Follow [SECURITY.md](https://github.com/smuniharish/xstructured/blob/master/SECURITY.md).
