# xstructured Agent Skill validation

This directory documents the repeatable validation process for the canonical
skill. It is intentionally not a second runtime test suite and does not provide
platform-specific adapters.

The Agent Skills specification was checked at
[agentskills.io/specification](https://agentskills.io/specification). It
defines `name` and `description` as the required frontmatter. No official
validator is specified there, so validation combines structural checks with
source-backed review.

## Structural validation

For every change:

1. Confirm [`../skills/xstructured/SKILL.md`](../skills/xstructured/SKILL.md)
   exists and starts with YAML frontmatter.
2. Confirm `name` is exactly `xstructured` (the directory name), contains only
   lowercase letters and hyphens, and is at most 64 characters.
3. Confirm `description` is non-empty, at most 1024 characters, and states
   both the capability and when to activate it.
4. Confirm only `name` and `description` appear in frontmatter unless the
   current specification and a demonstrated host requirement justify more.
5. Resolve every relative Markdown target in the skill, its references, and
   this directory; no target may point at a deleted file.
6. Confirm the distribution contains a single canonical knowledge source in
   `skills/xstructured/` and no duplicate skill copies.
7. Search the distribution for stale package names, invented CLI commands,
   credentials, or unrelated project guidance.

## Source-accuracy review

Review every code snippet and factual claim against the source of truth:

| Claim area | Source of truth |
| --- | --- |
| Public import and package version | [package exports](https://github.com/smuniharish/xstructured/blob/master/src/xstructured/__init__.py) |
| Runnable integration and agent boundary | [LangChain integration](https://xstructured.readthedocs.io/en/latest/integrations/langchain/) |
| Architecture and request lifecycle | [Architecture overview](https://xstructured.readthedocs.io/en/latest/architecture/overview/) |
| Why the wrapper exists | [Why xstructured?](https://xstructured.readthedocs.io/en/latest/integrations/why-xstructured/) |
| Parser limits and safety configuration | [Project README](https://github.com/smuniharish/xstructured/blob/master/README.md) and [Security](https://xstructured.readthedocs.io/en/latest/security/) |
| Examples and runnable patterns | [Examples](https://github.com/smuniharish/xstructured/tree/master/examples) |

If a behavior lacks an implementation, test, or authoritative document in this
repository, omit it from the skill rather than infer an API.

## Agent-task matrix

The following matrix was reviewed against the canonical
[`../skills/xstructured/SKILL.md`](../skills/xstructured/SKILL.md), its
references, the runtime implementation, and the repository examples.

| Task | Activates | Grounded route | Avoids |
| --- | --- | --- | --- |
| “Wrap an existing custom Runnable with typed output.” | Yes | `references/integration.md` and the `with_xstructured_output` examples. | Inventing wrapper APIs or changing orchestration. |
| “I need Pydantic validation after a model returns free-form text.” | Yes | `StructuredParser` and recovery guidance. | Manual string slicing or ad hoc JSON scraping. |
| “The model output is inside markdown or commentary.” | Yes | Recovery and parsing references. | Blind regex extraction. |
| “I want ordered streaming of prose plus typed data.” | Yes | `stream`/`astream` and event protocol docs. | Reconstructing event ordering in application code. |
| “Use this with a LangChain agent graph.” | Yes | `create_agent` adapter guidance. | Rewriting the graph to fit a non-native contract. |
| “I need to bound untrusted model output.” | Yes | `ParserConfig` and security docs. | Hidden or permissive parsing limits. |
| “A malformed response is recoverable.” | Yes | `RecoveryConfig` and structured repair flow. | Endless retries or silent bypass of validation. |

## Repository validation

Skill-only work should at least run the structural and source review above and
review the resulting Git diff. If runtime files change, run the CI-equivalent
checks in the project README and documentation build.
