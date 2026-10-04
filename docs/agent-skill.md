# Agent Skill

The repository ships an [Agent Skill](https://agentskills.io) that teaches AI coding
agents how to use `xstructured` correctly: when to choose it over native structured
output, how to wrap chat models, chains, and agents, how to stream, configure limits,
handle errors, and test integrations offline.

The skill lives in
[`skills/xstructured/`](https://github.com/smuniharish/xstructured/tree/master/skills/xstructured)
and follows the Agent Skills specification:

```text
skills/xstructured/
├── SKILL.md                      # When to use the skill, workflow, and rules
└── references/
    ├── api.md                    # Public API at a glance
    ├── integration.md            # Chat models, chains, agents, LangGraph
    ├── streaming.md              # Stream events and composition
    ├── configuration.md          # Limits, recovery, and repair
    └── troubleshooting.md        # Errors, causes, and fixes
```

Agents load `SKILL.md` when a task matches its description, and read a reference file only
when they need it.

## Install

With the [skills CLI](https://skills.sh):

```bash
npx skills add smuniharish/xstructured --skill xstructured
```

Or copy the `skills/xstructured/` directory, including `references/`, into the skills
directory your agent reads, for example:

| Agent | Project scope | User scope |
| --- | --- | --- |
| Claude Code | `.claude/skills/xstructured/` | `~/.claude/skills/xstructured/` |
| GitHub Copilot | `.github/skills/xstructured/` | `~/.copilot/skills/xstructured/` |
| Agents following the shared convention | `.agents/skills/xstructured/` | `~/.agents/skills/xstructured/` |

Locations differ between agents and versions; check your agent's documentation. Restart
or reload the agent after installing, and update by replacing the whole directory.

## Validate

The skill is validated with the specification's reference validator and by the test
suite, which checks its metadata, links, and code:

```bash
uvx --from skills-ref agentskills validate skills/xstructured
```
