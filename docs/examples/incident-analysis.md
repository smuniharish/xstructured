# Incident analysis

An operator's report becomes fields for an incident ticket, while the model's one-sentence
assessment is kept as prose for the hand-off.

```python title="examples/incident_analysis.py"
--8<-- "examples/incident_analysis.py"
```

## Output

=== "Live"

    ```text
    === Incident analysis (live: gpt-5.6-luna) ===
    Severity:       high
    Summary:        Checkout errors increased to 35% at 09:12 UTC following release 2026.09.18 and fell to 1% within five minutes of rollback.
    Probable cause: A production regression introduced by release 2026.09.18.
    Immediate:      ['Keep the rollback in place and monitor checkout error rates and transaction success.', 'Verify error rates remain near baseline across affected regions and services.']
    Follow-up:      ['Review release 2026.09.18 changes and logs to identify the defective component.', 'Add targeted regression tests and validate the fix in staging before redeployment.']
    Explanation:    The checkout error spike was most likely caused by a regression in release 2026.09.18, and rollback successfully mitigated the incident.
    ```

=== "Offline"

    ```text
    === Incident analysis (offline: scripted model) ===
    Severity:       high
    Summary:        Checkout errors rose to 35% after release 2026.09.18; rolling back reduced them to 1% within five minutes.
    Probable cause: A regression introduced by release 2026.09.18.
    Immediate:      ['Keep the rollback in place', 'Watch checkout error rates']
    Follow-up:      ['Bisect the release for the failing change', 'Add a checkout canary before the next deploy']
    Explanation:    The rollback points to the release as the trigger; the root cause still needs review.
    ```

Treat `probable_cause` as input to a human review, not as a confirmed root cause.
