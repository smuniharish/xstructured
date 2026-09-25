# Agent Skills

`xstructured` publishes one portable Agent Skill that teaches coding agents how
to integrate, configure, debug, test, and optimize the existing
`xstructured` library. The skill is documentation and procedural guidance; it
is not a Python runtime component and does not change how `xstructured` is
installed.

| Component | Location |
| --- | --- |
| xstructured Python runtime | [`src/xstructured/`](https://github.com/smuniharish/xstructured/tree/master/src/xstructured) |
| Canonical Agent Skill | [`skills/xstructured/`](https://github.com/smuniharish/xstructured/tree/master/skills/xstructured) |
| Canonical instructions | [`SKILL.md`](https://github.com/smuniharish/xstructured/blob/master/skills/xstructured/SKILL.md) |

The skill follows the [Agent Skills specification](https://agentskills.io/specification)
and contains the required `name` and `description` frontmatter. There is no
separate Claude, Codex, Cursor, or Copilot copy of the skill.

## Install from skills.sh

The [skills CLI](https://www.skills.sh/docs/cli) installs skills from a GitHub
source. Install the `xstructured` skill directory directly:

```bash
npx skills add https://github.com/smuniharish/xstructured/tree/master/skills/xstructured
```

This is the portable installation route. Follow the CLI's current target
selection prompts, then verify that it placed the `xstructured` folder in the
target agent's supported skills directory. The shorthand
`npx skills add xstructured` is not a valid source identifier.

## Install manually

First obtain the canonical skill directory from the
[repository](https://github.com/smuniharish/xstructured/tree/master/skills/xstructured).
Copy the complete `xstructured` directory, including `SKILL.md` and
`references/`, into one of the host-specific locations below. Do not copy only
`SKILL.md`, because it links to the bundled references.

### Claude Code

Claude Code discovers standalone skills in:

| Scope | Destination |
| --- | --- |
| Current repository | `.claude/skills/xstructured/` |
| All local projects | `~/.claude/skills/xstructured/` |

Start or restart Claude Code after copying the directory. Claude can select the
skill when its description matches the task, or you can invoke it with
`/xstructured`.

### Codex

Codex discovers repository skills by scanning `.agents/skills` from the working
directory to the repository root. Copy the directory to:

| Scope | Destination |
| --- | --- |
| Current repository | `.agents/skills/xstructured/` |
| All local projects | `~/.agents/skills/xstructured/` |

Codex detects changes automatically; restart it if the skill does not appear.
Invoke it explicitly with `$xstructured` or use `/skills` to inspect available
skills.

### Cursor

Cursor supports the standard `.agents/skills` locations, which makes the Codex
layout above portable. It also supports Cursor-specific locations:

| Scope | Destination |
| --- | --- |
| Current repository | `.agents/skills/xstructured/` or `.cursor/skills/xstructured/` |
| All local projects | `~/.agents/skills/xstructured/` or `~/.cursor/skills/xstructured/` |

Restart Cursor after copying the directory. In Agent chat, type `/` and select
`xstructured` to attach it to a message; Cursor can also activate it from its
description.

### GitHub Copilot

GitHub Copilot supports the standard `.agents/skills` layout, and also the
following project and personal locations:

| Scope | Destination |
| --- | --- |
| Current repository | `.agents/skills/xstructured/`, `.github/skills/xstructured/`, or `.claude/skills/xstructured/` |
| All local projects | `~/.agents/skills/xstructured/` or `~/.copilot/skills/xstructured/` |

For Copilot CLI, start a new session or run `/skills reload`, then verify the
skill with `/skills info xstructured`. You can explicitly request it in a prompt
using `/xstructured`.

### Other Agent Skills-compatible hosts

Use the host's documented skill directory and copy the complete `xstructured`
folder there. The canonical skill relies only on the standard `SKILL.md`
frontmatter and sibling `references/` directory, so it does not require a
host-specific adapter.

If a host needs package metadata, a registry entry, or a plugin manifest, follow
that host's current official documentation and add only a thin adapter that
points to this canonical skill. Do not duplicate the skill instructions.

## Update and verify

To update a manual installation, replace the complete installed `xstructured`
folder with the latest directory from the repository, then restart or reload the
host.

After installation, confirm all of the following:

1. The directory name is `xstructured`.
2. `SKILL.md` and `references/` are present in that directory.
3. The host lists `xstructured` as an available skill, if it exposes a skill
   listing command or UI.
4. A task involving LangChain Runnable integration, schema validation, parsing,
   streaming, or recovery can activate or explicitly invoke the skill.

See the distribution's [README](https://github.com/smuniharish/xstructured/blob/master/skills/README.md)
and [validation process](https://github.com/smuniharish/xstructured/blob/master/validation/README.md)
for maintenance details.
