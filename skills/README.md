# xstructured Agent Skills

This directory is the canonical Agent Skills distribution for the `xstructured`
Python package.

Official documentation: https://xstructured.readthedocs.io/
Repository: https://github.com/smuniharish/xstructured

It is not a runtime library and does not add behavior at import time. It
contains the guidance agents need when integrating, configuring, debugging, or
validating the package against existing LangChain and Pydantic workflows.

| Component | Location | Purpose |
| --- | --- | --- |
| xstructured runtime | [`src/xstructured/`](../src/xstructured) | Published Python package and supported public API. |
| Canonical agent skill | [`xstructured/SKILL.md`](xstructured/SKILL.md) | Agent-oriented instructions for integration and validation. |
| Reference material | [`xstructured/references/`](xstructured/references) | Concise architecture, integration, configuration, and troubleshooting notes. |
| Skill validation | [`../validation/README.md`](../validation/README.md) | Structural and source-grounded validation for the distribution. |

The canonical skill follows the Agent Skills `SKILL.md` format: a single
repository-scoped Markdown instruction file with required `name` and
`description` YAML frontmatter. The `name` matches the containing directory
(`xstructured`).

Use the canonical skill when working on LangChain Runnable integration, schema
injection, extraction recovery, typed streaming, or structured-output validation
without inventing a second parsing framework.
