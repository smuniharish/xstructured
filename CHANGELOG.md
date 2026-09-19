# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial repository foundation: `pyproject.toml` (uv-managed dependency
  groups, Ruff/Flake8/Pyrefly/pytest configuration), Apache-2.0 `LICENSE`,
  `README.md`, `CONTRIBUTING.md`.
- Documentation site (MkDocs Material, published via Read the Docs) covering
  concepts, architecture, integrations, examples, and an API reference
  generated with mkdocstrings.
- Environment-gated example scripts demonstrating `with_xstructured_output`
  with a single `create_agent` agent, a two-agent pipeline, and an optional
  `deepagents` deep agent.
- Mermaid diagram sources and a pinned rendering script producing the PNGs
  used in the documentation.
- CI workflows validating lint, format, types, tests, packaging, and the
  documentation build.
- Named schemas: `StructuredParser`, `with_xstructured_output`,
  `schema_instructions`, and `fingerprint_schema` accept a mapping of names
  to schema targets (or a pre-built `xstructured.NamedSchemas`), so a single
  response can be validated against one of several allowed shapes via an
  explicit `{"schema": "<name>", "payload": <value>}` envelope. Adds
  `NamedSchemaSpec`, `NamedSchemas`, `inspect_named_schemas`, and
  `ParseResult.schema_name` / `XStructuredResult.schema_name`.
- Optional, bounded LLM-assisted repair: `with_xstructured_output(...,
  repair=..., repair_config=...)` retries a failed parse by asking a
  user-supplied repair `Runnable` to fix the response, bounded by
  `RepairConfig.max_attempts` and re-validated by the same
  `StructuredParser`. Adds `RepairConfig`, `RepairError`, and
  `ParseResult.repaired` / `XStructuredResult.repaired`. Off by default;
  never invoked unless a `repair` Runnable is supplied.
