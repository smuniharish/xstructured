# xstructured Agent Skills

This directory distributes two Agent Skills that teach coding agents to use
the `xstructured` package correctly. They are not part of the Python package
and add no runtime behavior.

| Skill | Use it to |
| --- | --- |
| [`xstructured`](skills/xstructured/SKILL.md) | Add xstructured to an application: wrap chat models and graphs, add the agent middleware, use the output parser, stream prose and data, configure limits, recovery, and repair, trace with OpenTelemetry, test offline, and troubleshoot |
| [`xstructured-extend`](skills/xstructured-extend/SKILL.md) | Extend xstructured: write a `JsonDecoder`, `RecoveryStrategy`, `Observer`, or another extension point, and test it with the contract suites |

Install both with the [skills CLI](https://github.com/vercel-labs/skills),
which finds them through [`skills.sh.json`](../skills.sh.json):

```bash
npx skills add smuniharish/xstructured                          # both
npx skills add smuniharish/xstructured --skill xstructured      # one
```

Other ways to install are in the
[documentation](https://xstructured.readthedocs.io/en/latest/agent-skills/install/).

## Layout

Each skill follows the [Agent Skills specification](https://agentskills.io/specification):

```text
skills/<skill>/
├── SKILL.md      # frontmatter, workflow, rules, gotchas, links to every file
├── references/   # focused documents, one level deep, read only when a task needs them
├── scripts/      # offline checks with --help, --json, and meaningful exit codes
├── assets/       # templates the agent copies into the project, each with its tests
└── evals/        # evals.json, trigger_queries.json, and the input files they use
```

| Skill | Scripts | Assets |
| --- | --- | --- |
| `xstructured` | `verify_setup.py`: parser, wrapper, and streaming offline; the agent middleware too when installed (`--agents` to require it) | `test_structured_output.py` |
| `xstructured-extend` | `check_extension.py`: runs the contract for any decoder, recovery strategy, or observer factory | `decoder_template.py`, `observer_template.py`, `test_extensions.py` |

Every Agent Skills host reads the same directories, so there is no separate
copy for Claude Code, Codex, Cursor, or GitHub Copilot.

## Format

- `name` matches the directory. The `description` starts with "Use this skill
  when", names near misses, and hands over to the other skill where they
  meet.
- `license`, `compatibility`, and `metadata.version` are set. The version
  equals the `xstructured` release the skill describes.
- `SKILL.md` stays short and links every reference with the task that needs
  it. Scripts and assets are referenced by paths relative to the skill
  directory.

## Maintaining the skills

When the public API or documented behavior changes:

1. Update the affected skill, and `metadata.version` in both skills with each
   release.
2. Check every changed snippet and claim against the code, tests, or
   documentation. Leave out anything that is not implemented.
3. Add or update an eval when the change affects what an agent should do.
4. Run the checks in [`validation/README.md`](validation/README.md).

The skills are covered by the repository's Apache License 2.0; see
[LICENSE](../LICENSE).
