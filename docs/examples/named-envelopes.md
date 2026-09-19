# Multiple named envelopes

Use `multiple_envelopes=True` when one response contains separately framed
payloads:

```python
chain = with_xstructured_output(
    model,
    {"finding": Finding, "recommendation": Recommendation},
    multiple_envelopes=True,
)
result = chain.invoke("Analyze this incident.")

finding = result.structured["finding"]
recommendation = result.structured["recommendation"]
```

Each name must be configured, must occur at most once, and is validated with
its own Pydantic schema. Unknown or duplicate names fail explicitly.

## Live run output

```text
Analysis:
<xstructured name="finding">
{"title": "Insufficient incident details were provided to determine the checkout failure mode, impact, or root cause.", "severity": "unknown"}
</xstructured>

Recommendation:
<xstructured name="recommendation">
{"owner": "Incident Commander", "action": "Provide the incident timeline, affected checkout components, error rates, customer impact, recent changes, and relevant logs for analysis."}
</xstructured>
```

This output was captured from a live provider run. The model correctly returned
both configured names; the values reflect the intentionally underspecified
prompt and may differ when the prompt includes a detailed incident report.

The single-schema default remains one unnamed `<xstructured>...</xstructured>`
envelope. This mode is available for invocation and async invocation; streaming
multiple independently named envelopes is intentionally not yet exposed as a
single stream contract.
