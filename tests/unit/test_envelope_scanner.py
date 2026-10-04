from __future__ import annotations

import pytest

from xstructured import (
    EnvelopeScanner,
    EnvelopeSpec,
    EnvelopeState,
    LimitExceededError,
    ScanEvent,
)


def test_delimiters_split_across_chunks_are_found() -> None:
    scanner = EnvelopeScanner(EnvelopeSpec("[[", "]]"))

    first = scanner.feed("prefix [")
    second = scanner.feed('[{"ok":')
    third = scanner.feed("true}]] suffix")

    assert first == ScanEvent(
        EnvelopeState.SEEKING_START, text_before="prefix "
    )
    assert second.started
    assert second.payload_delta == '{"ok"'
    assert third.completed
    assert third.payload == '{"ok":true}'
    assert third.text_after == " suffix"
    assert scanner.complete
    assert scanner.payload == '{"ok":true}'
    assert scanner.span == (7, 22)


def test_one_chunk_releases_every_part_in_order() -> None:
    event = EnvelopeScanner().feed('Hi <xstructured>{"a": 1}</xstructured> bye')

    assert event == ScanEvent(
        EnvelopeState.COMPLETE,
        text_before="Hi ",
        started=True,
        payload_delta='{"a": 1}',
        completed=True,
        text_after=" bye",
        payload='{"a": 1}',
    )


def test_text_after_completion_is_released_unchanged() -> None:
    scanner = EnvelopeScanner()
    scanner.feed("<xstructured>{}</xstructured>")

    event = scanner.feed(" more <xstructured>{}</xstructured>")

    assert event.text_after == " more <xstructured>{}</xstructured>"
    assert event.payload == "{}"
    assert scanner.span == (0, 29)


def test_closing_delimiter_inside_a_json_string_is_ignored() -> None:
    scanner = EnvelopeScanner()
    scanner.feed('<xstructured>{"a": "</xstru')
    event = scanner.feed('ctured>"}</xstructured>')

    assert event.payload == '{"a": "</xstructured>"}'


def test_finalize_releases_held_back_text() -> None:
    scanner = EnvelopeScanner()

    assert scanner.feed("no envelope <xstr").text_before == "no en"
    assert scanner.finalize() == ScanEvent(
        EnvelopeState.SEEKING_START, text_before="velope <xstr"
    )
    assert not scanner.complete


def test_finalize_releases_an_unterminated_payload() -> None:
    scanner = EnvelopeScanner()
    scanner.feed('<xstructured>{"a": 1}</xs')

    assert scanner.finalize() == ScanEvent(
        EnvelopeState.COLLECTING, payload_delta='{"a": 1}</xs'
    )
    assert scanner.state is EnvelopeState.COLLECTING


def test_finalize_after_completion_reports_the_payload() -> None:
    scanner = EnvelopeScanner()
    scanner.feed("<xstructured>{}</xstructured>")

    assert scanner.finalize() == ScanEvent(EnvelopeState.COMPLETE, payload="{}")


def test_payload_and_envelope_limits_are_enforced() -> None:
    spec = EnvelopeSpec("<s>", "</s>")

    with pytest.raises(
        LimitExceededError, match="payload exceeds"
    ) as payload_error:
        EnvelopeScanner(spec, max_payload_chars=3).feed("<s>1234567")
    with pytest.raises(
        LimitExceededError, match="Envelope exceeds"
    ) as envelope_error:
        EnvelopeScanner(spec, max_envelope_chars=9).feed("<s>123</s>")
    with pytest.raises(LimitExceededError, match="Envelope exceeds"):
        EnvelopeScanner(spec, max_envelope_chars=9).feed("<s>1234567")

    assert payload_error.value.limit == "max_payload_chars"
    assert payload_error.value.maximum == 3
    assert envelope_error.value.limit == "max_envelope_chars"
    assert envelope_error.value.text == "<s>123"


def test_payload_at_the_exact_limit_is_accepted() -> None:
    scanner = EnvelopeScanner(
        EnvelopeSpec("<s>", "</s>"), max_payload_chars=3, max_envelope_chars=10
    )

    assert scanner.feed("<s>123</s>").payload == "123"


def test_limits_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        EnvelopeScanner(max_payload_chars=0)


def test_chunks_must_be_strings() -> None:
    with pytest.raises(TypeError, match="strings"):
        EnvelopeScanner().feed(b"bytes")  # type: ignore[arg-type]


def test_default_spec_is_exposed() -> None:
    assert EnvelopeScanner().spec == EnvelopeSpec()
    assert EnvelopeScanner().payload is None
