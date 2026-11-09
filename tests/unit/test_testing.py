from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from typing import Any, override

import pytest
from langchain_core.messages import AIMessage

from tests.support import RecordingObserver
from xstructured import (
    AttributeValue,
    InstructionInjector,
    JsonDecoder,
    Observation,
    Observer,
    OutputTextExtractor,
    RecoveryStrategy,
)
from xstructured.testing import (
    InstructionInjectorContract,
    JsonDecoderContract,
    ObserverContract,
    OutputTextExtractorContract,
    RecoveryStrategyContract,
    ScriptedChatModel,
)


class TestRecordingObserver(ObserverContract):
    def make_observer(self) -> Observer:
        return RecordingObserver()


class LenientDecoder(JsonDecoder):
    @override
    def decode(self, text: str, *, max_nesting_depth: int) -> Any:
        return None

    @override
    def json_text(self, text: str, value: Any) -> str:
        return '"changed"'


class RepeatingStrategy(RecoveryStrategy):
    @override
    def candidates(self, text: str) -> Iterator[str]:
        yield text.strip()
        yield text.strip()


class SilentStrategy(RecoveryStrategy):
    @override
    def candidates(self, text: str) -> Iterator[str]:
        return iter(())


class EmptyExtractor(OutputTextExtractor):
    @override
    def text(self, output: Any) -> str:
        return ""


class MutatingInjector(InstructionInjector):
    @override
    def inject(self, value: Any, instructions: str) -> Any:
        value.append(instructions)
        return value


class IdentityInjector(InstructionInjector):
    @override
    def inject(self, value: Any, instructions: str) -> Any:
        return value


class NoObservation(Observer):
    @override
    def start(
        self, operation: str, attributes: Mapping[str, AttributeValue]
    ) -> Observation:
        return object()  # type: ignore[return-value]


def _decoders(decoder: object) -> JsonDecoderContract:
    class Suite(JsonDecoderContract):
        def make_decoder(self) -> JsonDecoder:
            return decoder  # type: ignore[return-value]

    return Suite()


def _strategies(strategy: object) -> RecoveryStrategyContract:
    class Suite(RecoveryStrategyContract):
        def make_strategy(self) -> RecoveryStrategy:
            return strategy  # type: ignore[return-value]

    return Suite()


def _extractors(extractor: object) -> OutputTextExtractorContract:
    class Suite(OutputTextExtractorContract):
        def make_extractor(self) -> OutputTextExtractor:
            return extractor  # type: ignore[return-value]

        def make_output(self, text: str) -> Any:
            return text

    return Suite()


def _injectors(injector: object) -> InstructionInjectorContract:
    class Suite(InstructionInjectorContract):
        def make_injector(self) -> InstructionInjector:
            return injector  # type: ignore[return-value]

        def make_input(self) -> Any:
            return ["question"]

    return Suite()


def _observers(observer: object) -> ObserverContract:
    class Suite(ObserverContract):
        def make_observer(self) -> Observer:
            return observer  # type: ignore[return-value]

    return Suite()


@pytest.mark.parametrize(
    ("check", "message"),
    [
        (_decoders(object()).test_is_a_json_decoder, "JsonDecoder subclass"),
        (_decoders(LenientDecoder()).test_decodes_standard_json, "json.loads"),
        (
            _decoders(
                LenientDecoder()
            ).test_rejects_invalid_json_with_value_error,
            "invalid JSON",
        ),
        (
            _decoders(
                LenientDecoder()
            ).test_rejects_documents_nested_too_deeply,
            "max_nesting_depth",
        ),
        (
            _decoders(
                LenientDecoder()
            ).test_json_text_is_standard_json_for_the_value,
            "json_text",
        ),
        (
            _strategies(object()).test_is_a_recovery_strategy,
            "RecoveryStrategy subclass",
        ),
        (
            _strategies(
                SilentStrategy()
            ).test_first_candidate_is_the_text_as_given,
            "stripped text",
        ),
        (
            _strategies(
                RepeatingStrategy()
            ).test_candidates_are_distinct_non_empty_substrings,
            "distinct",
        ),
        (
            _extractors(object()).test_is_an_output_text_extractor,
            "OutputTextExtractor subclass",
        ),
        (
            _extractors(EmptyExtractor()).test_reads_the_text_of_an_output,
            "response text",
        ),
        (
            _extractors(
                EmptyExtractor()
            ).test_chunk_texts_concatenate_to_the_response,
            "concatenate",
        ),
        (
            _extractors(EmptyExtractor()).test_rejects_outputs_without_text,
            "TypeError",
        ),
        (
            _injectors(object()).test_is_an_instruction_injector,
            "InstructionInjector subclass",
        ),
        (
            _injectors(
                MutatingInjector()
            ).test_returns_a_new_value_without_modifying_the_input,
            "must not modify",
        ),
        (
            _injectors(
                IdentityInjector()
            ).test_returns_a_new_value_without_modifying_the_input,
            "carrying the instructions",
        ),
        (
            _injectors(IdentityInjector()).test_rejects_unsupported_inputs,
            "TypeError",
        ),
        (_observers(object()).test_is_an_observer, "Observer subclass"),
        (
            _observers(NoObservation()).test_records_a_success,
            "Observation subclass",
        ),
    ],
)
def test_contracts_report_broken_implementations(
    check: Callable[[], None], message: str
) -> None:
    with pytest.raises(AssertionError, match=message):
        check()


async def test_scripted_models_replay_messages_and_accept_tools() -> None:
    call = AIMessage(
        content="", tool_calls=[{"name": "search", "args": {}, "id": "1"}]
    )
    model = ScriptedChatModel.of(call, "done")

    bound = model.bind_tools([{"name": "search"}], tool_choice="auto")

    assert bound is model
    assert (await model.ainvoke("q")).tool_calls[0]["name"] == "search"
    assert (await model.ainvoke("q")).text == "done"
