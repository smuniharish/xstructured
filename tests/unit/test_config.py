from __future__ import annotations

import pytest
from pydantic import ValidationError

from xstructured import ParserConfig, RecoveryConfig, RepairConfig


def test_defaults_are_safe_and_conservative() -> None:
    config = ParserConfig()

    assert config.max_input_chars == 1_000_000
    assert config.max_envelope_chars == 1_000_000
    assert config.max_payload_chars == 1_000_000
    assert config.max_nesting_depth == 100
    assert config.require_envelope is False
    assert config.recovery == RecoveryConfig()
    assert RecoveryConfig().max_candidates == 4
    assert RepairConfig() == RepairConfig(enabled=True, max_attempts=1)


@pytest.mark.parametrize(
    "field",
    [
        "max_input_chars",
        "max_envelope_chars",
        "max_payload_chars",
        "max_nesting_depth",
    ],
)
def test_limits_must_be_positive(field: str) -> None:
    with pytest.raises(ValidationError):
        ParserConfig(**{field: 0})


def test_nesting_depth_has_a_safe_ceiling() -> None:
    assert ParserConfig(max_nesting_depth=1_000).max_nesting_depth == 1_000
    with pytest.raises(ValidationError):
        ParserConfig.model_validate({"max_nesting_depth": 1_001})


@pytest.mark.parametrize("value", [0, 5])
def test_recovery_candidate_budget_is_bounded(value: int) -> None:
    with pytest.raises(ValidationError):
        RecoveryConfig(max_candidates=value)


@pytest.mark.parametrize("value", [0, 6])
def test_repair_attempts_are_bounded(value: int) -> None:
    with pytest.raises(ValidationError):
        RepairConfig(max_attempts=value)


@pytest.mark.parametrize("model", [ParserConfig, RecoveryConfig, RepairConfig])
def test_configs_are_frozen_and_reject_unknown_fields(model: type) -> None:
    config = model()
    field = next(iter(model.model_fields))
    with pytest.raises(ValidationError):
        setattr(config, field, getattr(config, field))
    with pytest.raises(ValidationError):
        model(unknown=True)


def test_nested_recovery_config_accepts_a_mapping() -> None:
    config = ParserConfig.model_validate({"recovery": {"enabled": False}})

    assert config.recovery.enabled is False
