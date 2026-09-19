# Security

![Security boundaries](assets/diagrams/security-boundaries.png)

Model output is untrusted input. `xstructured` provides bounded extraction,
strict JSON decoding, and Pydantic validation; it does **not** make model output
safe to authorize actions.

## Guarantees and limits

- `ParserConfig.max_input_chars` rejects oversized input before parsing.
- Envelope closing delimiters inside JSON strings are ignored.
- Pydantic validates types and constraints, and can forbid unknown fields.
- Recovery never executes content and never rewrites malformed JSON.
- The parser does not sanitize HTML, SQL, shell arguments, URLs, or file paths.
- A schema-valid value may still violate application authorization or business
  rules.

Use strict schemas with bounded strings and collections where practical. Apply
authorization and domain checks after parsing and before database writes, tool
calls, filesystem access, or network requests. Never interpolate parsed values
into commands or queries; use parameterized APIs.

Keep credentials out of prompts, schemas, benchmark fixtures, exceptions, and
logs. The bundled [benchmark](benchmarks.md) uses only local synthetic data and
makes no network requests.

For ambiguous repeated envelopes, apply the
[multiple-payload guidance](concepts/multiple-payloads.md).
