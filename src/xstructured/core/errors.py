"""Exception hierarchy.

Every exception raised by xstructured derives from `XStructuredError`. Failures caused
by model output derive from `ParseError` and keep the offending text on the exception
for debugging; the text is never part of ``str(error)``, so logging an error does not
leak model output.
"""

from __future__ import annotations

__all__ = [
    "EnvelopeError",
    "LimitExceededError",
    "ParseError",
    "RecoveryError",
    "RepairError",
    "SchemaError",
    "XStructuredError",
]


class XStructuredError(Exception):
    """Base class for every exception raised by xstructured."""


class SchemaError(XStructuredError):
    """A schema target cannot be introspected, or named schemas are misconfigured."""


class EnvelopeError(XStructuredError):
    """An envelope specification is invalid, or an envelope scanner is misused."""


class ParseError(XStructuredError):
    """Model output could not be turned into a schema-valid value.

    Args:
        message: Description of the failure.
        text: The model output that failed to parse.

    Attributes:
        text: The model output that failed to parse.
    """

    def __init__(self, message: str, *, text: str = "") -> None:
        super().__init__(message)
        self.text = text


class LimitExceededError(ParseError):
    """Model output exceeded a configured resource limit.

    Limit violations are never retried with LLM-assisted repair.

    Args:
        message: Description of the failure.
        text: The model output (or the part received so far) that exceeded the limit.
        limit: Name of the exceeded `ParserConfig` field.
        maximum: The configured maximum.

    Attributes:
        limit: Name of the exceeded `ParserConfig` field, for example ``"max_input_chars"``.
        maximum: The configured maximum.
    """

    def __init__(
        self, message: str, *, text: str = "", limit: str = "", maximum: int = 0
    ) -> None:
        super().__init__(message, text=text)
        self.limit = limit
        self.maximum = maximum


class RecoveryError(ParseError):
    """Every recovery candidate failed JSON decoding or schema validation.

    Args:
        message: Description of the failure.
        text: The model output that failed to parse.
        failures: One failure description per attempted candidate.

    Attributes:
        failures: One concise failure description per attempted candidate, in the
            order the candidates were tried.
    """

    def __init__(
        self, message: str, *, text: str = "", failures: tuple[str, ...] = ()
    ) -> None:
        super().__init__(message, text=text)
        self.failures = failures


class RepairError(ParseError):
    """Opt-in LLM-assisted repair did not produce a schema-valid response.

    `text` is the original model output; the last repair attempt's failure is available
    as ``__cause__``.

    Args:
        message: Description of the failure.
        text: The original model output.
        attempts: Number of repair attempts made.
        failures: One failure description per repair attempt.

    Attributes:
        attempts: Number of repair attempts made.
        failures: One failure description per repair attempt, in order.
    """

    def __init__(
        self,
        message: str,
        *,
        text: str = "",
        attempts: int = 0,
        failures: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message, text=text)
        self.attempts = attempts
        self.failures = failures
