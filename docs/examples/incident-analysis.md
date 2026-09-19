# Incident analysis

[`examples/incident_analysis.py`](https://github.com/xstructured/xstructured/blob/main/examples/incident_analysis.py)
turns an operator report into fields suitable for an incident ticket:

```python
class IncidentAnalysis(BaseModel):
    severity: str
    summary: str
    probable_cause: str
    immediate_actions: list[str] = Field(min_length=1)
    follow_up_actions: list[str] = Field(min_length=1)

analysis = with_xstructured_output(model, IncidentAnalysis).invoke(
    [HumanMessage(content=operator_report)]
).structured
```

The example uses a rollback observation, but does not claim that the model's
probable cause is a confirmed root cause; treat it as an input to human review.

## Live run output

```text
=== Incident analysis ===
Severity: High
Summary: Checkout errors increased to 35% at 09:12 UTC following release 2026.09.18. Rolling back the release reduced errors to 1% within five minutes.
Probable cause: A regression introduced by release 2026.09.18 caused checkout failures.
Immediate actions: ['Roll back release 2026.09.18', 'Monitor checkout error rates and related service health', 'Confirm error rates remain near the pre-release baseline']
Follow-up actions: ['Investigate the changes in release 2026.09.18 and identify the failing checkout component', 'Review logs, traces, and failed transactions from the incident window', 'Add or strengthen automated checkout regression tests', 'Document the incident and validate release safeguards before redeployment']
```
