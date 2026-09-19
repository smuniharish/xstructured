# Multiple payloads and LLM-assisted repair

[`examples/multiple_payloads_repair.py`](https://github.com/xstructured/xstructured/blob/main/examples/multiple_payloads_repair.py)
uses the configured OpenAI-compatible provider for both the primary model and
the explicitly supplied repair Runnable:

```python
chain = with_xstructured_output(
    model,
    {"finding": Finding, "action": Action},
    multiple=True,
    repair=model,
    repair_config=RepairConfig(max_attempts=2),
)
result = chain.invoke("Review this incident report and return every finding and action.")
```

The primary response contains one `<xstructured>` envelope whose JSON value is
an array. Each item is dispatched to its named Pydantic schema, so the result
can contain heterogeneous `Finding` and `Action` values:

```python
for item in result.structured:
    print(item)
```

Repair is not unconditional. The second model call is made only if extraction,
JSON decoding, or Pydantic validation fails. The repaired response is parsed
with the same schemas and resource limits, and `result.repaired` records
whether repair was needed. `max_attempts` bounds additional calls.

## Live run output

The following output was captured from a live provider run. Repair was
configured but was not needed because the first response validated:

```text
=== Multiple payloads with LLM-assisted repair ===
Validated payload count: 3
- Finding(title='Checkout failures increased after the release', severity='high', evidence='Checkout failures rose following the release.')
- Finding(title='Rollback reduced checkout errors', severity='high', evidence='Error rates decreased after the rollback.')
- Action(owner='Release engineering', action='Add a canary check before the next deployment', priority='high')
Repair attempted: False
```

When a provider returns malformed or schema-invalid output on the first call,
the same example may instead report `Repair attempted: True`.

## Run with a real provider

```powershell
uv sync --group examples
$env:EXPLABS_API_KEY = "..."
$env:EXPLABS_MODEL = "gpt-5.6-luna"
$env:EXPLABS_BASE_URL = "https://api.experientiallabs.ai/v1"
uv run python examples/multiple_payloads_repair.py
```

The credential is read locally and is never part of the package or
documentation.
