# Multi-agent pipeline

An extractor agent turns an expense report into an `ExpenseClaim`, and a reviewer agent
checks the claim against a policy and returns a `ClaimReview`. Each agent is wrapped
independently, so the hand-off between them is a validated object rather than free text.

```python title="examples/multi_agent_pipeline.py"
--8<-- "examples/multi_agent_pipeline.py"
```

## Output

=== "Live"

    ```text
    === Multi-agent pipeline (live: gpt-5.6-luna) ===
    Claim:  ExpenseClaim(amount_usd=63.5, category='Transportation', description='Taxi from the airport to the client site')
    Review: ClaimReview(approved=True, reason='Approved: Transportation expense is $63.50, below the $75 receipt requirement, and contains no alcohol.')
    ```

=== "Offline"

    ```text
    === Multi-agent pipeline (offline: scripted model) ===
    Claim:  ExpenseClaim(amount_usd=63.5, category='transportation', description='Taxi from the airport to the client site')
    Review: ClaimReview(approved=True, reason='Under the $75 receipt threshold and not alcohol.')
    ```

`ExpenseClaim.amount_usd` is constrained with `Field(gt=0)`; a negative or missing amount
would stop the pipeline with a validation error before the reviewer runs.
