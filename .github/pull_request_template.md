<!--
Thanks for contributing to xstructured! Please fill out this template; it
helps reviewers understand and validate your change quickly.
-->

## Summary

<!-- What does this PR change, and why? -->

## Related issue(s)

<!-- Link any related issues, e.g. "Closes #123". -->

## Type of change

- [ ] Bug fix
- [ ] New feature (extension point, option, integration)
- [ ] Documentation
- [ ] Refactor / internal cleanup (no behavior change)
- [ ] Other (describe above)

## Checklist

- [ ] I read [CONTRIBUTING.md](../CONTRIBUTING.md).
- [ ] New/changed public behavior is covered by tests.
- [ ] `uv run ruff check .` and `uv run ruff format --check .` pass.
- [ ] `uv run pyrefly check` passes.
- [ ] `uv run pytest --cov` passes with 100% coverage.
- [ ] `uv run zensical build --strict` and `uv run python scripts/check_site_links.py`
      pass, and diagrams were re-rendered if a `diagrams/*.mmd` source changed.
- [ ] Relevant docs under `docs/` and the agent skill were updated (if this
      changes public API, configuration, or behavior).
- [ ] `CHANGELOG.md` has an entry under `[Unreleased]` (if this is a
      user-visible change).

## Data and telemetry impact

<!--
Does this change what is sent to the model, what reaches an Observer or
OpenTelemetry span, or what an exception carries? Describe the effect, or
write "None". Observation attributes never contain prompt or response text.
-->
