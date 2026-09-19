"""Configuration for structured parsing."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecoveryConfig(BaseModel):
    """Controls conservative normalization before retrying JSON parsing."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = True
    strip_markdown_fences: bool = True
    strip_surrounding_text: bool = True
    max_candidates: int = Field(default=8, ge=1, le=100)


class RepairConfig(BaseModel):
    """Controls the optional, bounded LLM-assisted repair fallback.

    Repair only runs when the caller explicitly supplies a repair
    ``Runnable`` (for example via
    ``with_xstructured_output(..., repair=repair_runnable)``); this config
    only tunes how that opt-in fallback behaves once wired in. It is never
    consulted when no repair ``Runnable`` is supplied, so existing
    single-schema callers are unaffected by its defaults.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = True
    max_attempts: int = Field(default=1, ge=1, le=5)


class ParserConfig(BaseModel):
    """Controls parser limits and recovery behavior."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_input_chars: int = Field(default=1_000_000, ge=1)
    max_envelope_chars: int = Field(default=1_000_000, ge=1)
    max_payload_chars: int = Field(default=1_000_000, ge=1)
    max_nesting_depth: int = Field(default=100, ge=1)
    recovery: RecoveryConfig = Field(default_factory=RecoveryConfig)
    require_envelope: bool = False

    @field_validator(
        "max_input_chars",
        "max_envelope_chars",
        "max_payload_chars",
        "max_nesting_depth",
    )
    @classmethod
    def validate_positive_limit(cls, value: int) -> int:
        if value < 1:
            raise ValueError("resource limits must be positive")
        return value
