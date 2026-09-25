# Configuration

Configure the parsing, recovery, and repair behavior with the public config
objects from the package root:

- `ParserConfig`
- `RecoveryConfig`
- `RepairConfig`

Authoritative sources:

- [xstructured package exports](https://github.com/smuniharish/xstructured/blob/master/src/xstructured/__init__.py)
- [Benchmarks](https://xstructured.readthedocs.io/en/latest/benchmarks/)
- [Security](https://xstructured.readthedocs.io/en/latest/security/)

## Core rules

- Prefer the defaults unless the application has a measured need to tighten or
  loosen limits.
- Set explicit limits when handling untrusted model output.
- Reject malformed, duplicate-key, non-standard JSON values with the formal
  parser settings instead of basic string checks.
- Use bounded repair rather than open-ended retries.
- Keep the schema and the parsed result aligned; do not swap schemas silently.

## Typical safe configuration

```python
from xstructured import ParserConfig, StructuredParser

parser = StructuredParser(
    ContactInfo,
    config=ParserConfig(
        max_input_chars=100_000,
        max_envelope_chars=50_000,
        max_payload_chars=40_000,
        max_nesting_depth=32,
    ),
)
```

The same configuration pattern applies to `with_xstructured_output` when a
service needs a stricter boundary for model-generated content.
