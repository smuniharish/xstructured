from __future__ import annotations

import pytest

from xstructured.parser.recovery import recovery_candidates


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
