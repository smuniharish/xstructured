"""Incremental decoder shared by synchronous and asynchronous integrations."""

from __future__ import annotations

from typing import Generic, TypeVar

from xstructured.core import ParseError
from xstructured.envelope import EnvelopeSpec
from xstructured.parser import StructuredParser

from .events import StreamEvent, StreamEventKind

T = TypeVar("T")


class StreamDecoder(Generic[T]):
    """Decode arbitrary text chunks into ordered protocol events."""

    def __init__(
        self,
        parser: StructuredParser[T],
        envelope: EnvelopeSpec,
    ) -> None:
        self._parser = parser
        self._envelope = envelope
        self._buffer = ""
        self._payload_parts: list[str] = []
        self._payload_chars = 0
        self._text_parts: list[str] = []
        self._sequence = 0
        self._started = False
        self._completed = False
        self._input_chars = 0
        self._in_string = False
        self._escaped = False

    @property
    def text(self) -> str:
        """Natural-language text observed outside the envelope."""
        return "".join(self._text_parts)

    @property
    def payload(self) -> str:
        """Structured JSON text observed inside the envelope."""
        return "".join(self._payload_parts)

    @property
    def complete(self) -> bool:
        """Whether the closing delimiter has been observed."""
        return self._completed

    @property
    def next_sequence(self) -> int:
        """Sequence number that will be assigned to the next event."""
        return self._sequence

    def feed(self, chunk: str) -> list[StreamEvent[T]]:
        """Accept one chunk and return all newly available events."""
        if not isinstance(chunk, str):
            raise TypeError("Stream chunks must be strings")
        if not chunk:
            return []

        self._input_chars += len(chunk)
        if self._input_chars > self._parser.config.max_input_chars:
            raise ParseError(
                "Stream input exceeds configured limit of "
                f"{self._parser.config.max_input_chars} characters",
                "",
            )
        self._buffer += chunk
        events: list[StreamEvent[T]] = []

        if not self._started:
            start_at = self._buffer.find(self._envelope.start)
            if start_at < 0:
                safe_length = max(
                    0,
                    len(self._buffer) - len(self._envelope.start) + 1,
                )
                events.extend(self._emit_text(self._take(safe_length)))
                return events
            events.extend(self._emit_text(self._take(start_at)))
            self._take(len(self._envelope.start))
            self._started = True
            events.append(self._event(StreamEventKind.STRUCTURED_START))

        if not self._completed:
            self._validate_incomplete_envelope_limit()
            end_at = self._find_end()
            if end_at < 0:
                safe_length = max(
                    0,
                    len(self._buffer) - len(self._envelope.end) + 1,
                )
                events.extend(self._emit_structured(self._take(safe_length)))
                return events
            events.extend(self._emit_structured(self._take(end_at)))
            self._take(len(self._envelope.end))
            self._completed = True
            parsed = self._parser.parse(self._envelope.wrap(self.payload))
            events.append(
                self._event(
                    StreamEventKind.STRUCTURED_END,
                    structured=parsed.value,
                )
            )

        events.extend(self._emit_text(self._take(len(self._buffer))))
        return events

    def finalize(self) -> list[StreamEvent[T]]:
        """Flush trailing text and reject an incomplete protocol response."""
        if not self._started:
            self._emit_text(self._take(len(self._buffer)))
            raise ParseError("No xstructured envelope was found", self.text)
        if not self._completed:
            raise ParseError(
                "The xstructured envelope was not completed",
                self._envelope.start + self.payload + self._buffer,
            )
        return self._emit_text(self._take(len(self._buffer)))

    def _find_end(self) -> int:
        in_string = self._in_string
        escaped = self._escaped
        for index, character in enumerate(self._buffer):
            if in_string:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    in_string = False
            elif character == '"':
                in_string = True
            elif self._buffer.startswith(self._envelope.end, index):
                return index
        return -1

    def _take(self, length: int) -> str:
        value = self._buffer[:length]
        self._buffer = self._buffer[length:]
        return value

    def _emit_text(self, text: str) -> list[StreamEvent[T]]:
        if not text:
            return []
        self._text_parts.append(text)
        return [self._event(StreamEventKind.TEXT_DELTA, text=text)]

    def _emit_structured(self, text: str) -> list[StreamEvent[T]]:
        if not text:
            return []
        self._payload_parts.append(text)
        self._payload_chars += len(text)
        if self._payload_chars > self._parser.config.max_payload_chars:
            raise ParseError(
                "Stream payload exceeds configured limit of "
                f"{self._parser.config.max_payload_chars} characters",
                "",
            )
        self._in_string, self._escaped = _json_string_state(
            text,
            in_string=self._in_string,
            escaped=self._escaped,
        )
        return [self._event(StreamEventKind.STRUCTURED_DELTA, text=text)]

    def _validate_incomplete_envelope_limit(self) -> None:
        envelope_size = len(self._envelope.start) + self._payload_chars + len(self._buffer)
        if envelope_size > self._parser.config.max_envelope_chars:
            raise ParseError(
                "Stream envelope exceeds configured limit of "
                f"{self._parser.config.max_envelope_chars} characters",
                "",
            )

    def _event(
        self,
        kind: StreamEventKind,
        *,
        text: str | None = None,
        structured: T | None = None,
    ) -> StreamEvent[T]:
        event = StreamEvent(
            kind=kind,
            sequence=self._sequence,
            text=text,
            structured=structured,
        )
        self._sequence += 1
        return event


def _json_string_state(text: str, *, in_string: bool, escaped: bool) -> tuple[bool, bool]:
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
    return in_string, escaped
