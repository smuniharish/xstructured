# Evaluation

A skill is only useful when an agent picks it up for the right task and then
gets that task right. xstructured tests both, following the Agent Skills
guidance on
[evaluating skills](https://agentskills.io/skill-creation/evaluating-skills).

## Checked on every change

`tests/skill` runs offline with the rest of the test suite in CI. For both
skills, it checks:

- **Format.** The `skills-ref` reference validator accepts the frontmatter.
  `name` matches the directory, the description starts with "Use this skill
  when", and `metadata.version` equals the xstructured release.
- **Progressive disclosure.** `SKILL.md` stays under 500 lines and references
  are one level deep. Every reference is linked from `SKILL.md`, and every
  relative link resolves.
- **Bundled files.** `SKILL.md` mentions every script and asset, so the agent
  can find it.
- **Scripts.**
    - `verify_setup.py` passes with warnings as errors, prints valid JSON with
      `--json`, and requires the same dependency ranges as the package.
    - `check_extension.py` passes the decoder, strategy, and observer
      templates and names the promise a broken strategy violates. It exits
      with a distinct code when the factory can't be loaded.
- **Templates.** The structured-output test template and the extension
  templates pass their own tests.
- **Discovery.** The skills CLI finds both skills through `skills.sh.json`.

The documentation tests also check every Python block in the skills: it
parses, its imports exist, its keyword arguments are real parameters, and it
fits 80 columns. CI runs the setup check and the extension contracts again
against the built wheel, outside the development environment.

## Evaluated against real tasks

Each skill has an `evals/` folder:

| File | Contents |
| --- | --- |
| `evals.json` | Realistic tasks, each with input files, the expected result, and assertions a grader can verify |
| `trigger_queries.json` | 20 user requests: 10 that should load the skill and 10 near misses that shouldn't, split into training and validation sets |
| `files/` | The projects the tasks start from, such as a support bot that parses replies with a regex |

The tasks cover what agents get wrong without the skill:

| Skill | Tasks |
| --- | --- |
| `xstructured` | Replace a regex parser with a validated schema; give a `create_agent` agent a structured final answer while it keeps its tools; stream prose and then a card over server-sent events; fix the error from wrapping a `ChatPromptTemplate` |
| `xstructured-extend` | Write a decoder for a model that answers with Python dictionaries; send call metrics to Prometheus with an observer; fix a recovery strategy that fails its contract |

The near-miss trigger queries keep the two skills apart: many near misses for
`xstructured-extend` are tasks for `xstructured`, and the reverse. A test
checks that no query is meant to load both.

To evaluate a change to a skill, run each task with and without the skill in
a fresh agent session. Grade the outputs against the assertions, and compare
pass rates, time, and tokens. The
[validation guide](https://github.com/smuniharish/xstructured/blob/master/xstructured-skills/validation/README.md)
describes the workflow.

## Reviewed against the source

Automated checks can't tell whether guidance is correct. Each snippet and
claim in a skill is reviewed against the code, tests and documentation it
describes, and anything without an implementation is left out. The
[validation guide](https://github.com/smuniharish/xstructured/blob/master/xstructured-skills/validation/README.md)
lists the source of truth for each area.
