from __future__ import annotations

import pytest

from xstructured.contracts import RecoveryStrategy
from xstructured.parser.recovery import ConservativeRecovery


def recovery_candidates(
    text: str,
    *,
    strip_markdown_fences: bool = True,
    strip_surrounding_text: bool = True,
) -> list[str]:
    return list(
        ConservativeRecovery(
            strip_markdown_fences=strip_markdown_fences,
            strip_surrounding_text=strip_surrounding_text,
        ).candidates(text)
    )


def test_candidates_follow_the_documented_order() -> None:
    text = '```json\n{"a": [1]}\n```'

    assert list(recovery_candidates(text)) == [text, '{"a": [1]}', "[1]"]


@pytest.mark.parametrize(
    "fence",
    [
        "```json\n{}\n```",
        "```JSON\n{}\n```",
        "```\n{}\n```",
        "  ```json  \n{}```  \n",
    ],
)
def test_fence_variants_are_recognized(fence: str) -> None:
    assert "{}" in list(
        recovery_candidates(fence, strip_surrounding_text=False)
    )


def test_fences_inside_prose_are_left_to_surrounding_text_recovery() -> None:
    text = 'Here:\n```json\n{"a": 1}\n```\nThanks'

    assert list(recovery_candidates(text, strip_surrounding_text=False)) == [
        text
    ]
    assert '{"a": 1}' in list(recovery_candidates(text))


def test_candidates_are_deduplicated_and_never_empty() -> None:
    assert list(recovery_candidates('  {"a": 1}  ')) == ['{"a": 1}']
    assert list(recovery_candidates("   ")) == []


def test_recovery_strategies_can_be_disabled() -> None:
    text = 'Answer: {"a": 1}'

    assert list(recovery_candidates(text, strip_surrounding_text=False)) == [
        text
    ]


def test_brackets_in_the_wrong_order_produce_no_candidate() -> None:
    assert list(recovery_candidates("} then {")) == ["} then {"]


def test_strategy_is_a_recovery_strategy_with_a_readable_repr() -> None:
    strategy = ConservativeRecovery(strip_markdown_fences=False)

    assert isinstance(strategy, RecoveryStrategy)
    assert repr(strategy) == (
        "ConservativeRecovery(strip_markdown_fences=False, "
        "strip_surrounding_text=True)"
    )


def test_fences_can_be_left_untouched() -> None:
    text = "```json\n[1]\n```"

    assert recovery_candidates(
        text, strip_markdown_fences=False, strip_surrounding_text=False
    ) == [text]
