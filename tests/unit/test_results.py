from __future__ import annotations

import pytest

from tests.support import Answer
from xstructured import ParseResult, XStructuredResult


def test_parse_result_reports_whether_an_envelope_was_used() -> None:
    plain = ParseResult(value=Answer(value=1), raw="{}", json_text="{}")
    enveloped = ParseResult(
        value=1, raw="x", json_text="1", envelope_spans=((0, 1),)
    )

    assert not plain.envelope_found
    assert enveloped.envelope_found
    assert (plain.recovered, plain.repaired, plain.repair_attempts) == (
        False,
        False,
        0,
    )


def test_result_types_are_immutable() -> None:
    result = XStructuredResult(
        content="", structured=1, raw="", raw_text="", json_text="1"
    )

    assert dict(result.metadata) == {}
    with pytest.raises(AttributeError):
        result.content = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.metadata["key"] = "value"  # type: ignore[index]
