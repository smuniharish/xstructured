"""Incremental scanner for delimited structured payloads."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from xstructured.core.errors import EnvelopeError

from .spec import EnvelopeSpec


class EnvelopeState(StrEnum):
    SEEKING_START = "seeking_start"
    COLLECTING = "collecting"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class ScanEvent:
    """The scanner's observable state after accepting input."""

    state: EnvelopeState
    payload: str | None = None


class EnvelopeScanner:
    """Find one envelope across arbitrary text chunks."""

    def __init__(
        self,
        spec: EnvelopeSpec | None = None,
        *,
        max_envelope_chars: int = 1_000_000,
        max_payload_chars: int = 1_000_000,
    ) -> None:
        if max_envelope_chars < 1 or max_payload_chars < 1:
            raise ValueError("Envelope limits must be positive")
        self.spec = spec or EnvelopeSpec()
        self._max_envelope_chars = max_envelope_chars
        self._max_payload_chars = max_payload_chars
        self._state = EnvelopeState.SEEKING_START
        self._buffer = ""
        self._payload: str | None = None
        self._payload_parts: list[str] = []
        self._payload_chars = 0
        self._in_string = False
        self._escaped = False

    @property
    def state(self) -> EnvelopeState:
        return self._state

    @property
    def payload(self) -> str | None:
        return self._payload

    @property
    def complete(self) -> bool:
        return self._state is EnvelopeState.COMPLETE

    def feed(self, chunk: str) -> ScanEvent:
        """Accept a chunk and return the resulting scanner event."""
        if not isinstance(chunk, str):
            raise TypeError("Envelope scanner chunks must be strings")
        if self.complete:
            if chunk:
                raise EnvelopeError("Cannot feed data after envelope completion")
            return ScanEvent(self._state, self._payload)

        self._buffer += chunk
        if self._state is EnvelopeState.SEEKING_START:
            start_at = self._buffer.find(self.spec.start)
            if start_at < 0:
                self._buffer = (
                    self._buffer[-(len(self.spec.start) - 1) :] if len(self.spec.start) > 1 else ""
                )
                return ScanEvent(self._state)
            self._buffer = self._buffer[start_at + len(self.spec.start) :]
            self._state = EnvelopeState.COLLECTING

        end_at = _find_json_safe_delimiter(
            self._buffer,
            self.spec.end,
            in_string=self._in_string,
            escaped=self._escaped,
        )
        if end_at < 0:
            safe_length = max(0, len(self._buffer) - len(self.spec.end) + 1)
            self._append_payload(self._take(safe_length))
            self._validate_incomplete_limits()
            return ScanEvent(self._state)

        self._append_payload(self._take(end_at))
        envelope_size = len(self.spec.start) + self._payload_chars + len(self.spec.end)
        if envelope_size > self._max_envelope_chars:
            raise EnvelopeError(
                f"Envelope exceeds configured limit of {self._max_envelope_chars} characters"
            )
        self._take(len(self.spec.end))
        self._payload = "".join(self._payload_parts)
        self._buffer = ""
        self._state = EnvelopeState.COMPLETE
        return ScanEvent(self._state, self._payload)

    def finalize(self) -> str:
        """Return the payload, or raise when the envelope is incomplete."""
        if self._payload is None:
            raise EnvelopeError("No complete envelope was found")
        return self._payload

    def _validate_incomplete_limits(self) -> None:
        envelope_size = len(self.spec.start) + self._payload_chars + len(self._buffer)
        if envelope_size > self._max_envelope_chars:
            raise EnvelopeError(
                f"Envelope exceeds configured limit of {self._max_envelope_chars} characters"
            )

    def _append_payload(self, text: str) -> None:
        if not text:
            return
        self._payload_parts.append(text)
        self._payload_chars += len(text)
        if self._payload_chars > self._max_payload_chars:
            raise EnvelopeError(
                f"Envelope payload exceeds configured limit of {self._max_payload_chars} characters"
            )
        self._in_string, self._escaped = _json_string_state(
            text,
            in_string=self._in_string,
            escaped=self._escaped,
        )

    def _take(self, length: int) -> str:
        value = self._buffer[:length]
        self._buffer = self._buffer[length:]
        return value


def _find_json_safe_delimiter(
    text: str,
    delimiter: str,
    *,
    in_string: bool = False,
    escaped: bool = False,
) -> int:
    """Find a delimiter outside JSON strings, including escaped string content."""
    for index, character in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif text.startswith(delimiter, index):
            return index
    return -1


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
