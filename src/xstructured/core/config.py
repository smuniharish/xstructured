"""Configuration models for parsing, recovery, and repair."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ParserConfig", "RecoveryConfig", "RepairConfig"]


class RecoveryConfig(BaseModel):
    """Conservative recovery applied when a payload is not valid as given.

    Recovery only changes *which substring* of a response is parsed; it never rewrites
    JSON syntax. Candidates are tried in a fixed order: the text as given, the body of a
    Markdown code fence that spans the whole text, the outermost ``{...}`` substring,
    and the outermost ``[...]`` substring. Each candidate must decode as strict JSON and
    validate against the schema.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Try recovery candidates when the text as given does not validate.",
    )
    strip_markdown_fences: bool = Field(
        default=True,
        description="Try the body of a Markdown code fence that wraps the whole text.",
    )
    strip_surrounding_text: bool = Field(
        default=True,
        description="Try the outermost object or array substring, dropping surrounding prose.",
    )
    max_candidates: int = Field(
        default=4,
        ge=1,
        le=4,
        description="Maximum number of candidates to attempt, including the text as given.",
    )


class RepairConfig(BaseModel):
    """Bounds for the opt-in, LLM-assisted repair fallback.

    Repair only runs when a repair Runnable is passed to `with_xstructured_output`; this
    configuration is ignored otherwise.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Allow the configured repair Runnable to be called.",
    )
    max_attempts: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Maximum number of repair calls for one response.",
    )


class ParserConfig(BaseModel):
    """Resource limits and parsing behavior for untrusted model output."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_input_chars: int = Field(
        default=1_000_000,
        ge=1,
        description="Maximum length of a complete response, or of a whole stream.",
    )
    max_envelope_chars: int = Field(
        default=1_000_000,
        ge=1,
        description="Maximum length of one envelope, including its delimiters.",
    )
    max_payload_chars: int = Field(
        default=1_000_000,
        ge=1,
        description="Maximum length of one JSON payload.",
    )
    max_nesting_depth: int = Field(
        default=100,
        ge=1,
        le=1_000,
        description="Maximum nesting depth of JSON arrays and objects.",
    )
    recovery: RecoveryConfig = Field(
        default_factory=RecoveryConfig,
        description="Conservative recovery settings.",
    )
    require_envelope: bool = Field(
        default=False,
        description=(
            "Fail when no complete envelope is present instead of parsing the whole text. "
            "The default envelope is used when the parser has none configured."
        ),
    )
