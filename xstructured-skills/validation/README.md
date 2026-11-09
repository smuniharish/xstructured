# Validating the xstructured skills

The `xstructured` and `xstructured-extend` skills are validated in three ways:
automated checks on every change, evaluations against real tasks, and a
review of every claim against its source.

## Automated checks

Run from the repository root:

```bash
uv run pytest tests/skill
uvx --from skills-ref agentskills validate \
  xstructured-skills/skills/xstructured
uvx --from skills-ref agentskills validate \
  xstructured-skills/skills/xstructured-extend
```

`tests/skill` runs offline in continuous integration. For both skills it
checks that:

- the frontmatter passes `skills-ref`. `name` matches the directory, the
  description starts with "Use this skill when", `license` is `Apache-2.0`,
  and `metadata.version` equals the package version;
- `SKILL.md` has fewer than 500 lines and links every reference;
  `references/` is one level deep, and every relative link resolves;
- `SKILL.md` mentions every bundled script and asset;
- `evals/evals.json` and `evals/trigger_queries.json` are well formed. The
  trigger queries are balanced, split into training and validation sets, and
  no query triggers both skills;
- the skills CLI discovers both skills through `skills.sh.json`.

It also runs the bundled code:

- `xstructured/scripts/verify_setup.py` passes, with warnings treated as
  errors, prints valid JSON with `--json`, and requires the package's
  dependency ranges;
- `xstructured/assets/test_structured_output.py` passes;
- the `xstructured-extend` templates pass their contract and end-to-end tests;
- `xstructured-extend/scripts/check_extension.py` handles three cases:
    - it passes a conforming decoder and observer;
    - it names the promise a broken strategy violates;
    - it exits with code 2 for a factory it can't load.

The code blocks in every skill document follow the documentation rules in
`tests/docs`: they use the real public API and fit 80 columns.

CI also runs `verify_setup.py --agents` and `check_extension.py` against the
built wheel.

## Evaluations

Each skill has an `evals/` folder, in the format described in
[Evaluating skills](https://agentskills.io/skill-creation/evaluating-skills):

- `evals.json`: realistic tasks with input files, an expected result, and
  assertions a grader can verify.
- `trigger_queries.json`: 10 requests that should load the skill and 10 near
  misses that shouldn't, split 12/8 into training and validation.

To evaluate a change:

1. Copy each task's input files into fresh workspaces, one with the skill and
   one without.
2. Run each task in a new agent session. The session without the skill can
   read the installed package but not the skill, the docs, or the
   repository's source.
3. Grade every assertion as passed or failed, with the evidence. Record time
   and tool calls.
4. Compare the two variants. Change the skill where the agent went wrong with
   it, or where it did no better than without it, then run the evaluation
   again.

Keep workspaces and benchmark files out of the repository.

## Source review

Automated checks can't tell whether guidance is correct. For every change,
check each snippet and claim against its source:

| Claim area | Source of truth |
| --- | --- |
| Public imports, signatures, and the package version | [`src/xstructured/__init__.py`](../../src/xstructured/__init__.py), [`pyproject.toml`](../../pyproject.toml), and the [API reference](../../docs/api/index.md) |
| The wrapper, inputs, outputs, and streaming | [`src/xstructured/langchain/`](../../src/xstructured/langchain/), [LangChain](../../docs/integrations/langchain.md), and [streaming](../../docs/guide/streaming.md) |
| Agents and Deep Agents | [`src/xstructured/agents.py`](../../src/xstructured/agents.py) and [agents](../../docs/integrations/agents.md) |
| Parsing, limits, recovery, and repair | [`src/xstructured/parser/`](../../src/xstructured/parser/), [configuration](../../docs/guide/configuration.md), and [repair](../../docs/guide/repair.md) |
| Extension points and contracts | [`src/xstructured/contracts.py`](../../src/xstructured/contracts.py), [`src/xstructured/testing.py`](../../src/xstructured/testing.py), and [extension points](../../docs/guide/extension-points.md) |
| Observers and OpenTelemetry | [`src/xstructured/otel.py`](../../src/xstructured/otel.py), [observability](../../docs/guide/observability.md), and [OpenTelemetry](../../docs/integrations/opentelemetry.md) |
| Errors | [`src/xstructured/core/errors.py`](../../src/xstructured/core/errors.py) and [errors](../../docs/guide/errors.md) |
| Working patterns | [`examples/`](../../examples/) and [`tests/`](../../tests/) |

If a behavior has no implementation, test, or documentation, leave it out of
the skill rather than infer it.

## Routing matrix

Check that the descriptions send each task to the right skill:

| Task | Skill | Route | Avoids |
| --- | --- | --- | --- |
| "Return the answer and a validated ticket from one reply." | `xstructured` | `with_xstructured_output` once at module level; `ainvoke`; offline tests. | Hand-written JSON prompts and regexes. |
| "My agent should end with a typed booking." | `xstructured` | `XStructuredMiddleware` with bounded `repair_config`. | Wrapping the agent when the value belongs in state. |
| "Stream prose, then show a card." | `xstructured` | `wrapper.astream`, `TEXT_DELTA` and `STRUCTURED_END`. | A second model call for the card. |
| "Trace parsing in Jaeger." | `xstructured` | `OpenTelemetryObserver` and the `otel` extra. | Logging prompts or responses. |
| "Accept Python dicts from our model." | `xstructured-extend` | A `JsonDecoder` subclass, `JsonDecoderContract`, `check_extension.py`. | Disabling safety rules, or `eval()`. |
| "Prometheus metrics for every call." | `xstructured-extend` | The observer template and `ObserverContract`. | Free-text metric labels or blocking I/O. |
| "Make the model always produce JSON with fine-tuning." | Neither | Not this package's purpose. | Inventing capabilities. |
