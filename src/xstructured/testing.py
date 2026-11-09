"""Test helpers: an offline chat model and conformance tests for extension points.

`ScriptedChatModel` replays scripted responses, so chains and agents run
without credentials or network access.

Each ``*Contract`` class checks the promises one extension point makes to
xstructured. Subclass it in a test module, implement its ``make_*`` methods,
and your test runner collects one test per promise:

```python
from xstructured.testing import JsonDecoderContract


class TestMyDecoder(JsonDecoderContract):
    def make_decoder(self):
        return MyDecoder()
```

The tests are plain synchronous methods that raise `AssertionError` with a
descriptive message, so they run under pytest, or under unittest when the
subclass also inherits ``unittest.TestCase``. No test plugin is required.
"""

from __future__ import annotations

import copy
import json
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, override

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from .contracts import (
    InstructionInjector,
    JsonDecoder,
    Observation,
    Observer,
    OutputTextExtractor,
    RecoveryStrategy,
)

__all__ = [
    "InstructionInjectorContract",
    "JsonDecoderContract",
    "ObserverContract",
    "OutputTextExtractorContract",
    "RecoveryStrategyContract",
    "ScriptedChatModel",
]

_INSTRUCTIONS = "Respond inside <xstructured>...</xstructured>."


class ScriptedChatModel(GenericFakeChatModel):
    """Chat model that replays scripted responses in order and accepts tools.

    Responses may be strings or `AIMessage` values, including messages with
    tool calls for agent tests. Streaming splits each response on whitespace.

    Example:
        ```python
        import asyncio

        from xstructured.testing import ScriptedChatModel

        model = ScriptedChatModel.of("Hello!", "Goodbye!")


        async def main() -> None:
            first = await model.ainvoke("Hi")
            second = await model.ainvoke("Bye")
            assert (first.text, second.text) == ("Hello!", "Goodbye!")


        asyncio.run(main())
        ```
    """

    @classmethod
    def of(cls, *responses: str | AIMessage) -> ScriptedChatModel:
        """Return a model that replays *responses*."""
        return cls(messages=iter(responses))

    @override
    def bind_tools(
        self, tools: Sequence[Any], **kwargs: Any
    ) -> ScriptedChatModel:
        """Accept tool definitions; tool calls come only from scripted messages."""
        del tools, kwargs
        return self


def _check(condition: bool, message: str) -> None:  # noqa: FBT001
    if not condition:
        raise AssertionError(message)


class JsonDecoderContract(ABC):
    """Tests every promise a `JsonDecoder` makes to the parser."""

    @abstractmethod
    def make_decoder(self) -> JsonDecoder:
        """Return the decoder under test."""

    def test_is_a_json_decoder(self) -> None:
        """The decoder subclasses `JsonDecoder`."""
        _check(
            isinstance(self.make_decoder(), JsonDecoder),
            "make_decoder must return a JsonDecoder subclass instance",
        )

    def test_decodes_standard_json(self) -> None:
        """Standard JSON documents decode to the values `json.loads` returns."""
        decoder = self.make_decoder()
        for text in ('{"a": [1, 2.5, "x", null, true]}', "[]", '"text"', "7"):
            _check(
                decoder.decode(text, max_nesting_depth=10) == json.loads(text),
                f"decode({text!r}) must equal json.loads({text!r})",
            )

    def test_rejects_invalid_json_with_value_error(self) -> None:
        """Text that is not JSON raises `ValueError`."""
        try:
            self.make_decoder().decode('{"a": ', max_nesting_depth=10)
        except ValueError:
            return
        raise AssertionError("decode must raise ValueError for invalid JSON")

    def test_rejects_documents_nested_too_deeply(self) -> None:
        """Nesting deeper than *max_nesting_depth* raises `ValueError`."""
        try:
            self.make_decoder().decode("[[[1]]]", max_nesting_depth=2)
        except ValueError:
            return
        raise AssertionError(
            "decode must raise ValueError when nesting exceeds max_nesting_depth"
        )

    def test_json_text_is_standard_json_for_the_value(self) -> None:
        """`json_text` returns standard JSON that decodes to the decoded value."""
        decoder = self.make_decoder()
        text = '{"when": "2026-01-01", "items": [1, 2]}'
        value = decoder.decode(text, max_nesting_depth=10)
        json_text = decoder.json_text(text, value)
        _check(
            json.loads(json_text) == value,
            "json_text must be standard JSON that decodes to the decoded value",
        )


class RecoveryStrategyContract(ABC):
    """Tests every promise a `RecoveryStrategy` makes to the parser."""

    @abstractmethod
    def make_strategy(self) -> RecoveryStrategy:
        """Return the strategy under test."""

    def sample_texts(self) -> Sequence[str]:
        """Return responses to derive candidates from."""
        return (
            '{"a": 1}',
            '  {"a": 1}  ',
            '```json\n{"a": 1}\n```',
            'Here it is: {"a": [1]} thanks',
            "no json here",
        )

    def test_is_a_recovery_strategy(self) -> None:
        """The strategy subclasses `RecoveryStrategy`."""
        _check(
            isinstance(self.make_strategy(), RecoveryStrategy),
            "make_strategy must return a RecoveryStrategy subclass instance",
        )

    def test_first_candidate_is_the_text_as_given(self) -> None:
        """The first candidate is the stripped text."""
        strategy = self.make_strategy()
        for text in self.sample_texts():
            candidates = list(strategy.candidates(text))
            _check(
                bool(candidates) and candidates[0] == text.strip(),
                f"the first candidate for {text!r} must be the stripped text",
            )

    def test_candidates_are_distinct_non_empty_substrings(self) -> None:
        """Candidates never rewrite the text and are never repeated or empty."""
        strategy = self.make_strategy()
        for text in self.sample_texts():
            candidates = list(strategy.candidates(text))
            _check(
                all(
                    candidate and candidate in text for candidate in candidates
                ),
                f"candidates for {text!r} must be non-empty substrings",
            )
            _check(
                len(set(candidates)) == len(candidates),
                f"candidates for {text!r} must be distinct",
            )


class OutputTextExtractorContract(ABC):
    """Tests every promise an `OutputTextExtractor` makes to the wrapper."""

    @abstractmethod
    def make_extractor(self) -> OutputTextExtractor:
        """Return the extractor under test."""

    @abstractmethod
    def make_output(self, text: str) -> Any:
        """Return a complete output whose response text is *text*."""

    def make_chunks(self, text: str) -> Sequence[Any]:
        """Return stream chunks whose response texts concatenate to *text*."""
        return [self.make_output(text)]

    def test_is_an_output_text_extractor(self) -> None:
        """The extractor subclasses `OutputTextExtractor`."""
        _check(
            isinstance(self.make_extractor(), OutputTextExtractor),
            "make_extractor must return an OutputTextExtractor subclass instance",
        )

    def test_reads_the_text_of_an_output(self) -> None:
        """`text` returns the response text of a complete output."""
        text = 'Done. <xstructured>{"a": 1}</xstructured>'
        _check(
            self.make_extractor().text(self.make_output(text)) == text,
            "text must return the response text of make_output(text)",
        )

    def test_chunk_texts_concatenate_to_the_response(self) -> None:
        """`chunk_text` of every chunk joins into the response text."""
        text = 'Done. <xstructured>{"a": 1}</xstructured>'
        extractor = self.make_extractor()
        joined = "".join(
            extractor.chunk_text(chunk) for chunk in self.make_chunks(text)
        )
        _check(
            joined == text, "chunk texts must concatenate to the response text"
        )

    def test_rejects_outputs_without_text(self) -> None:
        """An output that carries no text raises `TypeError`."""
        try:
            self.make_extractor().text(object())
        except TypeError:
            return
        raise AssertionError(
            "text must raise TypeError for an object without text"
        )


class InstructionInjectorContract(ABC):
    """Tests every promise an `InstructionInjector` makes to the wrapper."""

    @abstractmethod
    def make_injector(self) -> InstructionInjector:
        """Return the injector under test."""

    @abstractmethod
    def make_input(self) -> Any:
        """Return an input the injector supports."""

    def test_is_an_instruction_injector(self) -> None:
        """The injector subclasses `InstructionInjector`."""
        _check(
            isinstance(self.make_injector(), InstructionInjector),
            "make_injector must return an InstructionInjector subclass instance",
        )

    def test_returns_a_new_value_without_modifying_the_input(self) -> None:
        """`inject` returns a changed copy and leaves the input as it was."""
        value = self.make_input()
        before = copy.deepcopy(value)
        injected = self.make_injector().inject(value, _INSTRUCTIONS)
        _check(value == before, "inject must not modify its input")
        _check(
            injected != value,
            "inject must return a value carrying the instructions",
        )

    def test_rejects_unsupported_inputs(self) -> None:
        """An input that cannot carry instructions raises `TypeError`."""
        try:
            self.make_injector().inject(object(), _INSTRUCTIONS)
        except TypeError:
            return
        raise AssertionError(
            "inject must raise TypeError for an unsupported input"
        )


class ObserverContract(ABC):
    """Tests every promise an `Observer` makes to the wrapper and middleware."""

    @abstractmethod
    def make_observer(self) -> Observer:
        """Return the observer under test."""

    def _start(self) -> Observation:
        observation = self.make_observer().start(
            "invoke", {"xstructured.schema_fingerprint": "0" * 64}
        )
        _check(
            isinstance(observation, Observation),
            "start must return an Observation subclass instance",
        )
        return observation

    def test_is_an_observer(self) -> None:
        """The observer subclasses `Observer`."""
        _check(
            isinstance(self.make_observer(), Observer),
            "make_observer must return an Observer subclass instance",
        )

    def test_records_a_success(self) -> None:
        """A started observation accepts `succeed` with result attributes."""
        self._start().succeed(
            {"xstructured.recovered": False, "xstructured.envelope_count": 1}
        )

    def test_records_a_failure_and_a_cancellation(self) -> None:
        """A started observation accepts `fail` with errors and cancellations."""
        self._start().fail(ValueError("invalid"))
        self._start().fail(GeneratorExit())
