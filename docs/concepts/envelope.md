# Envelope protocol

Model output is rarely *just* JSON: it usually includes a natural-language
preamble or follow-up ("Sure, here''s the result: ..."). The envelope
protocol asks the model to place its structured payload between two
delimiters (`<xstructured>` and `</xstructured>` by default) so it can be
extracted reliably, even when the delimiters arrive split across multiple
stream chunks.

```python
from xstructured import EnvelopeScanner, EnvelopeSpec

scanner = EnvelopeScanner(EnvelopeSpec("<result>", "</result>"))
scanner.feed("Sure, here you go: <result>")
scanner.feed('{"value": 1}')
scanner.feed("</result> Let me know if you need anything else.")

assert scanner.complete
assert scanner.finalize() == '{"value": 1}'
```

`EnvelopeScanner` is a small state machine (`seeking_start` ->
`collecting` -> `complete`) that never needs the full text in memory at
once, which is what makes it safe to use inside a streaming decoder (see
[Streaming](streaming.md)).

`EnvelopeSpec` also produces the wrapped instruction text used to ask a
model to use the envelope, via `schema_instructions(schema, envelope=spec.start)`
(see [Schema fingerprinting](schema.md)).
