# Install in your agent

Each skill is one directory with `SKILL.md` at its root: `xstructured` and
`xstructured-extend`. Every agent that supports the
[Agent Skills format](https://agentskills.io/specification) reads the same
directories, so there is no separate copy per agent.

## With the skills CLI

The [skills CLI](https://github.com/vercel-labs/skills) finds both skills in
the repository, detects the agents in your project, and installs the skills
into each agent you choose. It needs Node.js 22.20 or later.

```bash
# choose interactively
npx skills add smuniharish/xstructured
# only the core skill
npx skills add smuniharish/xstructured --skill xstructured
# only the extension skill
npx skills add smuniharish/xstructured --skill xstructured-extend
```

| Option | Effect |
| --- | --- |
| `-g` | Install for every project instead of the current one |
| `-a claude-code` | Install for one agent; see the CLI's [agent list](https://github.com/vercel-labs/skills/blob/main/docs/agents.md) |

## Manually

Copy each complete skill directory, including `SKILL.md`, `references/`,
`scripts/` and `assets/`, into one of the locations for your agent. The
[`xstructured`](https://github.com/smuniharish/xstructured/tree/master/xstructured-skills/skills/xstructured)
and [`xstructured-extend`](https://github.com/smuniharish/xstructured/tree/master/xstructured-skills/skills/xstructured-extend)
directories are in the xstructured repository. Their `evals/` folders only
test the skills, so you can leave them out.

=== "Claude Code"

    | Scope | Destination |
    | --- | --- |
    | Current repository | `.claude/skills/<skill>/` |
    | All local projects | `~/.claude/skills/<skill>/` |

    Restart Claude Code. It selects a skill when the task matches, or invoke
    it with `/xstructured` or `/xstructured-extend`. See
    [Claude Code Skills](https://code.claude.com/docs/en/skills).

=== "Codex"

    | Scope | Destination |
    | --- | --- |
    | Current repository | `.agents/skills/<skill>/` |
    | All local projects | `~/.agents/skills/<skill>/` |

    Codex detects new skills automatically; restart it if a skill doesn't
    appear. Invoke one with `$xstructured` or `$xstructured-extend`, or list
    skills with `/skills`. See
    [Codex Skills](https://learn.chatgpt.com/docs/build-skills).

=== "Cursor"

    | Scope | Destination |
    | --- | --- |
    | Current repository | `.agents/skills/<skill>/` or `.cursor/skills/<skill>/` |
    | All local projects | `~/.agents/skills/<skill>/` or `~/.cursor/skills/<skill>/` |

    Restart Cursor. In Agent chat, type `/` and select the skill, or let
    Cursor activate it from its description. See
    [Cursor Agent Skills](https://cursor.com/docs/skills).

=== "GitHub Copilot"

    | Scope | Destination |
    | --- | --- |
    | Current repository | `.agents/skills/<skill>/`, `.github/skills/<skill>/` or `.claude/skills/<skill>/` |
    | All local projects | `~/.agents/skills/<skill>/` or `~/.copilot/skills/<skill>/` |

    In Copilot CLI, start a new session or run `/skills reload`, then check
    with `/skills info xstructured`. Invoke a skill with `/xstructured` or
    `/xstructured-extend`. See
    [Adding agent skills for GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills).

=== "Other agents"

    Copy the skill folders into the skills directory your agent documents.
    The skills use only standard `SKILL.md` frontmatter, so they need no
    agent-specific adapter.

    If an agent needs a manifest or registry entry, add only a thin adapter
    that points to these directories. Don't copy the instructions.

## Verify

1. Each installed directory is named after its skill (`xstructured` or
   `xstructured-extend`) and contains `SKILL.md`.
2. Your agent lists the skills, if it has a skill list.
3. From your project's Python environment, the xstructured setup check
   passes:

    ```bash
    python <skills directory>/xstructured/scripts/verify_setup.py --agents
    ```

    ```text
    PASS  Python 3.12.16 (3.12 or newer required)
    PASS  xstructured 1.0.0 (1.x expected by this skill)
    PASS  langchain-core 1.7.6 (>=1.7.6,<2 required)
    PASS  pydantic 2.14.3 (>=2.14.3,<3 required)
    PASS  langchain 1.4.9 (>=1.4.9,<2 required)
    INFO  optional integrations: langgraph 1.2.20, deepagents 0.7.34, opentelemetry-api 1.45.2, langsmith 0.14.17
    PASS  parser extracts envelopes, recovers fenced JSON, and rejects bad output
    PASS  with_xstructured_output returns prose and a validated value
    PASS  astream yields protocol events (13 events)
    PASS  XStructuredMiddleware puts the validated answer in agent state
    All checks passed.
    ```

    Without `--agents`, the middleware check is skipped when the
    `xstructured[agents]` extra is missing, and the core checks still run.
    Add `--json` to print one JSON object.

4. If you installed `xstructured-extend`, its decoder template passes the
   decoder contract:

    ```bash
    cd <skills directory>/xstructured-extend
    python scripts/check_extension.py \
      decoder_template:PythonLiteralDecoder --path assets
    ```

    The last line is `All 5 promises hold.`

## Update

Run `npx skills update`, or replace the installed folders with the latest
directories from the repository, then restart or reload your agent. Each
skill's `metadata.version` matches the xstructured release it describes.
