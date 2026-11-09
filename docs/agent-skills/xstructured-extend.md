# The xstructured-extend skill

The `xstructured-extend` skill teaches a coding agent to customize how
xstructured parses, prompts, and reports. Every behavior is an abstract base
class with a default, and the skill covers all of them:

| Base class | Replace it to |
| --- | --- |
| `JsonDecoder` | accept a model's non-standard JSON, such as Python dictionaries |
| `RecoveryStrategy` | find the payload in a model's quirky output |
| `InstructionRenderer` | write the instructions in another language or style |
| `InstructionInjector` | add the instructions to inputs the default rejects |
| `OutputTextExtractor` | read text from outputs the default rejects |
| `RepairPromptBuilder` | change what the repair model is asked |
| `Observer` | send metrics to Prometheus, StatsD, Datadog, or any backend |

[:material-github: View on GitHub](https://github.com/smuniharish/xstructured/tree/master/xstructured-skills/skills/xstructured-extend){ .md-button }
[:material-download: Install](index.md#agentic-installation){ .md-button }

## When the agent uses it

The agent loads the skill to write, test, or debug such a subclass, including
a failing contract test from `xstructured.testing`. Before writing one, it
checks whether configuration already does the job: other delimiters, fewer
recovery candidates, strict validation, or another state key need no
subclass.

To add xstructured to an application, wire agents or LangGraph, configure
limits or repair, or turn on OpenTelemetry, it hands over to the
[xstructured skill](xstructured.md).

## Workflows

=== "A decoder or a recovery strategy"

    1. Copy `assets/decoder_template.py`. A decoder raises `ValueError` for
       text it rejects and keeps the `StrictJsonDecoder` safety rules; a
       strategy yields the stripped text first and only distinct, non-empty
       substrings.
    2. Copy `assets/test_extensions.py` and keep `JsonDecoderContract` or
       `RecoveryStrategyContract`.
    3. Run the tests, or `scripts/check_extension.py`. Fix the first broken
       promise and rerun until every promise holds.
    4. Pass it with `decoder=` or `recovery=`, and add an end-to-end test
       that replays a reply the default rejects.

=== "An observer"

    1. Copy `assets/observer_template.py` and point its `_record_*` methods
       at the metrics backend.
    2. Keep `ObserverContract`, plus an end-to-end test that asserts what
       the backend received.
    3. Run `scripts/check_extension.py`, then pass `observer=` to every
       wrapper and middleware.

=== "Injector, extractor, renderer, or repair prompt"

    1. Subclass the default when only part of its behavior changes.
    2. Test injectors with `InstructionInjectorContract` and extractors with
       `OutputTextExtractorContract`.
    3. Test renderers and repair prompts end to end with
       `ScriptedChatModel`.

Before finishing, the agent checks that:

- the class subclasses the matching base class;
- every contract test and an end-to-end test pass;
- nothing blocks the event loop, and no prompt or response text reaches
  telemetry.

## What's inside

```text
xstructured-extend/
├── SKILL.md                    # workflows, checklist, gotchas
├── references/
│   ├── extension-points.md     # every base class, signature, contract
│   └── observers.md            # lifecycle, attributes, rules
├── scripts/
│   └── check_extension.py      # runs a contract without pytest
├── assets/
│   ├── decoder_template.py     # PythonLiteralDecoder and LastLineFirst
│   ├── observer_template.py    # MetricsObserver for a metrics backend
│   └── test_extensions.py      # the contracts and end-to-end tests
└── evals/                      # test prompts, assertions, trigger queries
```

The templates run as they are: their tests pass against xstructured alone,
so the agent starts from working code and changes one piece at a time.

## The contract check

`scripts/check_extension.py` loads a factory, for example a class, detects
whether it builds a `JsonDecoder`, a `RecoveryStrategy`, or an `Observer`, and
runs every test of the matching contract against it, without pytest:

```bash
python scripts/check_extension.py myapp.parsing:LenientDecoder
```

```text
Checking a JsonDecoder
PASS  test_decodes_standard_json
PASS  test_is_a_json_decoder
PASS  test_json_text_is_standard_json_for_the_value
PASS  test_rejects_documents_nested_too_deeply
PASS  test_rejects_invalid_json_with_value_error
All 5 promises hold.
```

| Option | Effect |
| --- | --- |
| `--path DIR` | Import the factory's module from this directory instead of the current one |
| `--json` | Print one JSON object for the agent to parse |

It exits with `0` when every promise holds, `1` when one is broken, and `2`
when the factory can't be loaded or builds another kind of object.

## Learn more

- [Extension points](../guide/extension-points.md): every base class and
  its contract.
- [Observability](../guide/observability.md): the observer lifecycle and
  OpenTelemetry.
- [Customization example](../examples/customization.md): a custom
  renderer and observer in one application.
