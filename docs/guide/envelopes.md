<!-- docs-test: run -->

# Envelopes

Model responses rarely contain *only* JSON. The envelope protocol asks the model to place
its structured payload between two delimiters, `<xstructured>` and `</xstructured>` by
default, so it can be separated from the surrounding prose reliably:

```text
Here is the contact you asked for.
<xstructured>{"name": "Priya Shah", "email": "priya.shah@example.com"}</xstructured>
Let me know if you need anything else.
```

## Custom delimiters

`EnvelopeSpec` defines the delimiters. They must be distinct, contain a non-whitespace
character, and must not contain double quotes or backslashes, so they can never be
confused with JSON string content.

```python
from xstructured import EnvelopeSpec

spec = EnvelopeSpec("<result>", "</result>")
print(spec.wrap('{"value": 1}'))  # <result>{"value": 1}</result>
```

## Delimiters inside JSON strings

The closing delimiter only ends the envelope when it appears *outside* a JSON string, so a
payload may safely mention the delimiter itself:

```python
from xstructured import EnvelopeScanner

scanner = EnvelopeScanner()
scanner.feed('Note: <xstructured>{"text": "use </xstructured> to close"}')
scanner.feed("</xstructured> done")

assert scanner.payload == '{"text": "use </xstructured> to close"}'
```

## Incremental scanning

`EnvelopeScanner` accepts text in arbitrary chunks, even when a delimiter is split across
them. Each call to `feed` returns a `ScanEvent` describing the text it released, in stream
order: text before the envelope, payload text, and text after it. At most one delimiter's
length of input is held back at any time.

```python
from xstructured import EnvelopeScanner, EnvelopeSpec

scanner = EnvelopeScanner(EnvelopeSpec("<result>", "</result>"))
for chunk in ["Sure! <res", 'ult>{"value"', ": 1}</res", "ult> Anything else?"]:
    event = scanner.feed(chunk)
    print(
        event.state,
        repr(event.text_before),
        repr(event.payload_delta),
        repr(event.text_after),
    )

assert scanner.complete
assert scanner.payload == '{"value": 1}'
assert scanner.span == (6, 35)  # offsets of the envelope in all text fed so far
```

The scanner enforces `max_envelope_chars` and `max_payload_chars`, and raises
`LimitExceededError` as soon as an envelope grows past its limit instead of buffering
unbounded input.

## Named envelopes

Tag-style delimiters can carry a name, which lets one response hold several separately
validated payloads (see [Multiple payloads](multiple-payloads.md)):

```python
spec = EnvelopeSpec()
print(spec.wrap('{"title": "Checkout regression"}', name="finding"))
# <xstructured name="finding">{"title": "Checkout regression"}</xstructured>
```

Names use 1-64 letters, digits, `_`, `.`, or `-`.
