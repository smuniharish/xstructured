# The xstructured skill

The `xstructured` skill teaches a coding agent to add xstructured to an
application and work with it once it is there. It covers:

- wrapping a chat model, chain, or LangGraph graph with
  `with_xstructured_output`;
- adding `XStructuredMiddleware` to a `create_agent` or Deep Agents agent;
- using `XStructuredOutputParser` in a `prompt | model | parser` chain;
- streaming prose and a structured card to a UI;
- multiple and named payloads, bounded repair, and validation context;
- OpenTelemetry tracing and offline tests with `ScriptedChatModel`;
- troubleshooting `ParseError`, `RecoveryError`, `RepairError`, and
  `LimitExceededError`.

[:material-github: View on GitHub](https://github.com/smuniharish/xstructured/tree/master/xstructured-skills/skills/xstructured){ .md-button }
[:material-download: Install](index.md#agentic-installation){ .md-button }

## When the agent uses it

The agent loads the skill when an application needs natural-language text
and Pydantic-validated data from the same model response, or when xstructured
fails to parse a reply.

To write a custom decoder, recovery strategy, observer, or other extension
point, it hands over to [xstructured-extend](xstructured-extend.md). When only
the structured value is needed and the provider's native structured output
is enough, it doesn't add xstructured.

## Workflow

The skill gives the agent a checklist to keep current while it works:

```text
- [ ] 1. verify_setup.py passes
- [ ] 2. Schema is a Pydantic model with described fields
- [ ] 3. One attach mode chosen and wired once, at module level
- [ ] 4. Errors handled by type; repair bounded if used
- [ ] 5. Offline tests with ScriptedChatModel
- [ ] 6. Project tests and verify_setup.py pass again
```

The agent checks the environment before it changes anything and again when
it finishes, and it picks one attach mode for the code it finds:

| The code has | The agent uses |
| --- | --- |
| A chat model, chain, Runnable, or compiled graph | `with_xstructured_output` |
| `create_agent` or `create_deep_agent` | `XStructuredMiddleware` |
| A prompt template piped into a model | `XStructuredOutputParser` |
| Text from anywhere else | `StructuredParser` |

## What's inside

```text
xstructured/
├── SKILL.md                        # attach modes, workflow, rules, gotchas
├── references/
│   ├── api.md                      # imports, signatures, results, errors
│   ├── integration.md              # agents, LangGraph, parsers, prompts
│   ├── streaming.md                # stream events, StreamDecoder, UIs
│   ├── configuration.md            # envelopes, limits, recovery, repair
│   ├── observability.md            # observers and OpenTelemetry spans
│   └── troubleshooting.md          # symptoms, causes, fixes
├── scripts/
│   └── verify_setup.py             # offline environment and behavior check
├── assets/
│   └── test_structured_output.py   # pytest template for a wrapper and agent
└── evals/                          # test prompts, assertions, trigger queries
```

The agent always sees the skill's name and description. It reads `SKILL.md`
when a task matches, and opens a reference only when the task needs it, so a
simple task costs little context.

## The setup check

`scripts/verify_setup.py` runs offline in the project's Python environment.
It checks:

- the Python version, and the xstructured, LangChain Core, and Pydantic
  versions;
- LangChain, when the `agents` extra is installed;
- parsing, the wrapper, streaming, and the agent middleware, against a
  scripted model.

| Option | Effect |
| --- | --- |
| `--agents` | Fail when the `xstructured[agents]` extra is missing |
| `--json` | Print one JSON object, `{"ok", "summary", "checks"}`, for the agent to parse |

It exits with `0` when every check passes and `1` otherwise. Sample output is
on the [install page](install.md#verify).

## Rules the agent follows

- **Async first.** Call `ainvoke`, `astream`, and `abatch` from async code.
- **One contract.** Keep the `<xstructured>` envelope and let xstructured
  add the instructions; don't also ask for JSON in a hand-written prompt.
- **Never weaken validation** to make a test pass.
- **Bound repair** with `RepairConfig.max_attempts`, and never loop on
  `ParseError` by hand.
- **Keep output out of logs.** `ParseError.text` holds the model output and
  is never part of the message.
