# Multiple payloads and repair

One response carries a JSON array whose items name their schema, so a single reply can mix
`Finding` and `Action` values. A repair model gets at most two attempts to fix an invalid
reply. In offline mode the scripted first reply is deliberately invalid (unquoted keys),
so you can watch repair work.

```python title="examples/multiple_payloads_repair.py"
--8<-- "examples/multiple_payloads_repair.py"
```

## Output

=== "Live"

    ```text
    === Multiple payloads with bounded repair (live: gpt-5.6-luna) ===
    - Finding(title='Checkout failures increased after the release', severity='high')
    - Finding(title='Rollback restored the checkout error rate', severity='medium')
    - Action(owner='Release engineering', action='Add and require a checkout canary check before the next deployment', priority='high')
    Repaired: False (attempts: 0)
    ```

=== "Offline"

    ```text
    === Multiple payloads with bounded repair (offline: scripted model) ===
    - Finding(title='Checkout failures rose after the release', severity='high')
    - Finding(title='Rollback restored the error rate', severity='medium')
    - Action(owner='release-engineering', action='Add a checkout canary before the next deploy', priority='high')
    Repaired: True (attempts: 1)
    ```

The live model produced a valid response first time, so repair was never called. Repair
only runs after parsing and recovery fail, and its output is validated by the same parser.
See [Bounded repair](../guide/repair.md).
