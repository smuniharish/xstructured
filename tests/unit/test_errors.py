from __future__ import annotations

import pickle

import pytest

from xstructured import (
    EnvelopeError,
    LimitExceededError,
    ParseError,
    RecoveryError,
    RepairError,
    SchemaError,
    XStructuredError,
)


@pytest.mark.parametrize(
    "error_type",
    [
        SchemaError,
        EnvelopeError,
        ParseError,
        LimitExceededError,
        RecoveryError,
        RepairError,
    ],
)
def test_every_error_derives_from_the_base_class(
    error_type: type[Exception],
) -> None:
    assert issubclass(error_type, XStructuredError)


@pytest.mark.parametrize(
    "error_type", [LimitExceededError, RecoveryError, RepairError]
)
def test_output_errors_are_parse_errors(error_type: type[Exception]) -> None:
    assert issubclass(error_type, ParseError)


def test_message_never_includes_the_model_output() -> None:
    error = ParseError("could not parse", text="secret model output")

    assert str(error) == "could not parse"
    assert "secret" not in repr(error)
    assert error.text == "secret model output"


def test_error_attributes_default_to_empty_values() -> None:
    assert ParseError("m").text == ""
    limit = LimitExceededError("m")
    assert (limit.limit, limit.maximum) == ("", 0)
    assert RecoveryError("m").failures == ()
    repair = RepairError("m")
    assert (repair.attempts, repair.failures) == (0, ())


@pytest.mark.parametrize(
    "error",
    [
        SchemaError("schema"),
        EnvelopeError("envelope"),
        ParseError("parse", text="raw"),
        LimitExceededError(
            "limit", text="raw", limit="max_input_chars", maximum=10
        ),
        RecoveryError("recovery", text="raw", failures=("a", "b")),
        RepairError("repair", text="raw", attempts=2, failures=("x", "y")),
    ],
    ids=lambda error: type(error).__name__,
)
def test_errors_survive_pickling(error: Exception) -> None:
    restored = pickle.loads(pickle.dumps(error))  # noqa: S301 - round-trips a trusted value

    assert type(restored) is type(error)
    assert str(restored) == str(error)
    assert vars(restored) == vars(error)
