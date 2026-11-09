# Customization

A wrapper configured through its extension points: a custom
`InstructionRenderer` adds a house rule to the instructions, a custom
`Observer` records metrics, and `SchemaOptions` turns on Pydantic strict mode.

```python title="examples/customization.py"
--8<-- "examples/customization.py"
```

## Output

```text
=== Customized wrapper (offline: scripted model) ===
[metrics] invoke ok: recovered=False envelopes=1 response_chars=133
Meeting: Meeting(title='Platform review', date='2026-11-03', attendees=4)
House rule sent: True
```

Every extension point is an abstract base class with a default; see
[Extension points](../guide/extension-points.md) and
[Pydantic options](../guide/configuration.md#pydantic-options).
