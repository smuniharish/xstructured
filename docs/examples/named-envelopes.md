# Named envelopes

The model writes a short analysis with two separately named envelopes, one per schema.
`structured` is a dictionary keyed by envelope name, and `content` keeps the prose in
between.

```python title="examples/named_envelopes.py"
--8<-- "examples/named_envelopes.py"
```

## Output

=== "Live"

    ```text
    === Multiple named envelopes (live: gpt-5.6-luna) ===
    finding: Finding(title='The updated payment-provider client caused a card-payment checkout regression, producing a 35% error rate shortly after release.', severity='high')
    recommendation: Recommendation(owner='Payments Platform team', action='Add provider-client contract and integration tests for card payments, deploy future client changes through a canary rollout with card-specific error-rate alerts, and require rollback readiness before full release.')
    Prose: 'The 09:10 release introduced a regression in the payment-provider client. The timing of the card-only failures, their absence from other payment methods, and recovery immediately after rollback strongly indicate that client change as the primary cause. The incident affected a critical checkout path and was not caught before full deployment.'
    ```

=== "Offline"

    ```text
    === Multiple named envelopes (offline: scripted model) ===
    finding: Finding(title='Checkout regression in release 2026.09.18', severity='high')
    recommendation: Recommendation(owner='platform', action='Add a checkout canary to the deploy pipeline')
    Prose: 'Analysis: the error spike started with the 09:10 release.\n\nRecommendation: keep the rollback and add a guard rail.'
    ```

Unknown, duplicated, or unclosed envelopes are rejected with a `ParseError`. See
[Multiple payloads](../guide/multiple-payloads.md#separately-named-envelopes).
