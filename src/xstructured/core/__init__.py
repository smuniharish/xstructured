"""Configuration, exceptions, and result types."""

from .config import ParserConfig, RecoveryConfig, RepairConfig
from .errors import (
    EnvelopeError,
    LimitExceededError,
    ParseError,
    RecoveryError,
    RepairError,
    SchemaError,
    XStructuredError,
)
from .result import ParseResult, XStructuredResult

__all__ = [
    "EnvelopeError",
    "LimitExceededError",
    "ParseError",
    "ParseResult",
    "ParserConfig",
    "RecoveryConfig",
    "RecoveryError",
    "RepairConfig",
    "RepairError",
    "SchemaError",
    "XStructuredError",
    "XStructuredResult",
]
