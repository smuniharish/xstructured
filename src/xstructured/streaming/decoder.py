"""Incremental decoding of a response stream into protocol events."""

from __future__ import annotations

from xstructured.core.errors import LimitExceededError, ParseError
from xstructured.core.result import ParseResult
from xstructured.envelope.scanner import (
    EnvelopeScanner,
    EnvelopeState,
    ScanEvent,
)
from xstructured.envelope.spec import EnvelopeSpec
from xstructured.parser.parser import StructuredParser

from .events import StreamEvent, StreamEventKind

__all__ = ["StreamDecoder"]


class StreamDecoder[T]:
    """Turn text chunks into ordered `StreamEvent` values.

    The decoder emits `TEXT_DELTA` events for text outside the envelope,
    `STRUCTURED_START`, `STRUCTURED_DELTA` events for payload text, and
    `STRUCTURED_END` carrying the validated value. A response must contain exactly one
    complete envelope; the parser's envelope (or the default one) is used.

    Args:
        parser: Parser providing the schema, limits, recovery settings, and envelope.

    Raises:
        ValueError: If the parser expects named envelopes, which cannot be streamed.

    Example:
        ```python
        from pydantic import BaseModel
        from xstructured import StreamDecoder, StructuredParser


        class Answer(BaseModel):
            value: int


        decoder = StreamDecoder(StructuredParser(Answer))
        chunks = ["Hi <xstruc", 'tured>{"value": 4', "2}</xstructured> bye"]
        events = []
        for chunk in chunks:
            events.extend(decoder.feed(chunk))
        decoder.finalize()
        assert decoder.result.value == Answer(value=42)
        ```
    """

    def __init__(self, parser: StructuredParser[T]) -> None:
        if parser.multiple_envelopes:
            raise ValueError("Named envelopes cannot be streamed")
        self._parser = parser
        self._envelope = parser.envelope or EnvelopeSpec()
        self._scanner = EnvelopeScanner(
            self._envelope,
            max_envelope_chars=parser.config.max_envelope_chars,
            max_payload_chars=parser.config.max_payload_chars,
        )
        self._text_parts: list[str] = []
        self._payload_parts: list[str] = []
        self._input_chars = 0
        self._sequence = 0
        self._result: ParseResult[T] | None = None

    @property
    def text(self) -> str:
        """Natural-language text received outside the envelope so far."""
        return "".join(self._text_parts)

    @property
    def payload(self) -> str:
        """Payload text received inside the envelope so far."""
        return "".join(self._payload_parts)

    @property
    def complete(self) -> bool:
        """Whether the closing delimiter has been received."""
        return self._scanner.complete

    @property
    def result(self) -> ParseResult[T]:
        """The validated parse result of the payload.

        Raises:
            ParseError: If no complete envelope has been received yet.
        """
        if self._result is None:
            raise ParseError(
                "No complete envelope has been received yet", text=self.text
            )
        return self._result

    @property
    def next_sequence(self) -> int:
        """The sequence number the next event will receive."""
        return self._sequence

    def feed(self, chunk: str) -> list[StreamEvent[T]]:
        """Accept the next chunk and return the events it completes.

        Raises:
            TypeError: If *chunk* is not a string.
            LimitExceededError: If a resource limit is exceeded.
            ParseError: If the completed payload does not validate.
        """
        if not isinstance(chunk, str):
            raise TypeError("Stream chunks must be strings")
        self._input_chars += len(chunk)
        maximum = self._parser.config.max_input_chars
        if self._input_chars > maximum:
            raise LimitExceededError(
                f"Stream input exceeds the configured limit of {maximum} characters",
                text=self.text + self.payload + chunk,
                limit="max_input_chars",
                maximum=maximum,
            )
        return self._events(self._scanner.feed(chunk))

    def finalize(self) -> None:
        """Signal the end of the stream.

        Once the envelope is complete, all text has already been released by `feed`,
        so this only verifies that a complete envelope was received.

        Raises:
            ParseError: If no complete envelope was received. Text held back while
                looking for the envelope is included in the error's ``text``.
        """
        self._events(self._scanner.finalize())
        start, end = self._envelope.start, self._envelope.end
        if self._scanner.state is EnvelopeState.SEEKING_START:
            raise ParseError(
                f"No {start}...{end} envelope was found", text=self.text
            )
        if self._scanner.state is EnvelopeState.COLLECTING:
            raise ParseError(
                f"The {start} envelope was not closed with {end}",
                text=self.text + start + self.payload,
            )

    def _events(self, scan: ScanEvent) -> list[StreamEvent[T]]:
        events: list[StreamEvent[T]] = []
        if scan.text_before:
            events.append(self._text(scan.text_before))
        if scan.started:
            events.append(self._event(StreamEventKind.STRUCTURED_START))
        if scan.payload_delta:
            self._payload_parts.append(scan.payload_delta)
            events.append(
                self._event(
                    StreamEventKind.STRUCTURED_DELTA, text=scan.payload_delta
                )
            )
        if scan.completed and scan.payload is not None:
            self._result = self._parser.parse_payload(scan.payload)
            events.append(
                self._event(
                    StreamEventKind.STRUCTURED_END,
                    structured=self._result.value,
                )
            )
        if scan.text_after:
            events.append(self._text(scan.text_after))
        return events

    def _text(self, text: str) -> StreamEvent[T]:
        self._text_parts.append(text)
        return self._event(StreamEventKind.TEXT_DELTA, text=text)

    def _event(
        self,
        kind: StreamEventKind,
        *,
        text: str | None = None,
        structured: T | None = None,
    ) -> StreamEvent[T]:
        event: StreamEvent[T] = StreamEvent(
            kind=kind, sequence=self._sequence, text=text, structured=structured
        )
        self._sequence += 1
        return event
