"""Core configuration, errors, and result types."""

from .config import ParserConfig, RecoveryConfig, RepairConfig
from .errors import (
    EnvelopeError,
    ParseError,
    RecoveryError,
    RepairError,
    SchemaError,
    XStructuredError,
)
from .result import ParseResult

__all__ = [
    "EnvelopeError",
    "ParseError",
    "ParseResult",
    "ParserConfig",
    "RecoveryConfig",
    "RecoveryError",
    "RepairConfig",
    "RepairError",
    "SchemaError",
    "XStructuredError",
]
