import pytest

from xstructured.core import EnvelopeError
from xstructured.envelope import EnvelopeScanner, EnvelopeSpec, EnvelopeState


def test_scanner_handles_delimiters_split_across_chunks() -> None:
    scanner = EnvelopeScanner(EnvelopeSpec("[[", "]]"))

    assert scanner.feed("prefix [").state is EnvelopeState.SEEKING_START
    assert scanner.feed('[{"ok":').state is EnvelopeState.COLLECTING
    event = scanner.feed("true}]] suffix")

    assert event.state is EnvelopeState.COMPLETE
    assert event.payload == '{"ok":true}'
    assert scanner.finalize() == '{"ok":true}'


def test_scanner_rejects_nonempty_data_after_completion() -> None:
    scanner = EnvelopeScanner()
    scanner.feed("<xstructured>{}</xstructured>")

    with pytest.raises(EnvelopeError, match="after envelope completion"):
        scanner.feed("unexpected")


def test_envelope_spec_requires_distinct_nonempty_delimiters() -> None:
    with pytest.raises(EnvelopeError):
        EnvelopeSpec("", "]]")
    with pytest.raises(EnvelopeError):
        EnvelopeSpec("##", "##")


def test_scanner_enforces_payload_and_envelope_limits() -> None:
    spec = EnvelopeSpec("<s>", "</s>")

    with pytest.raises(EnvelopeError, match="payload exceeds"):
        EnvelopeScanner(spec, max_payload_chars=3).feed("<s>1234567")
    with pytest.raises(EnvelopeError, match="Envelope exceeds"):
        EnvelopeScanner(spec, max_envelope_chars=9).feed("<s>123</s>")


def test_scanner_allows_payload_at_exact_limit() -> None:
    scanner = EnvelopeScanner(EnvelopeSpec("<s>", "</s>"), max_payload_chars=3)

    assert scanner.feed("<s>123</s>").payload == "123"
