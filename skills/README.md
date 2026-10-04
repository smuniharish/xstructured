# Agent Skills

This directory contains the [Agent Skill](https://agentskills.io) for `xstructured`. It
teaches AI coding agents when and how to use the package; it is documentation, not part of
the installed library.

| Path | Purpose |
| --- | --- |
| [`xstructured/SKILL.md`](xstructured/SKILL.md) | Metadata, decision guide, workflow, core patterns, and rules. |
| [`xstructured/references/`](xstructured/references) | API, integration, streaming, configuration, and troubleshooting references loaded on demand. |

Install it with the [skills CLI](https://skills.sh):

```bash
npx skills add smuniharish/xstructured --skill xstructured
```

or copy the `xstructured/` directory into your agent's skills directory. See the
[documentation](https://xstructured.readthedocs.io/en/latest/agent-skill/) for agent-specific
locations.

The skill is validated with `uvx --from skills-ref agentskills validate skills/xstructured`
and by `tests/test_skill.py`, which checks its metadata, links, and code examples.
