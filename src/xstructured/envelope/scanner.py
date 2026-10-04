"""Incremental single-envelope scanner."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from xstructured._scan import OUTSIDE, scan_for_delimiter
from xstructured.core.errors import LimitExceededError

from .spec import EnvelopeSpec

__all__ = ["EnvelopeScanner", "EnvelopeState", "ScanEvent"]


class EnvelopeState(StrEnum):
    """Lifecycle of an `EnvelopeScanner`."""

    SEEKING_START = "seeking_start"
    """Looking for the opening delimiter."""
    COLLECTING = "collecting"
    """Inside the envelope, collecting payload text."""
    COMPLETE = "complete"
    """The closing delimiter was found."""


@dataclass(frozen=True, slots=True)
class ScanEvent:
    """What one `EnvelopeScanner.feed` or `EnvelopeScanner.finalize` call released.

    Within one event the parts always occur in stream order: `text_before`, the opening
    delimiter (`started`), `payload_delta`, the closing delimiter (`completed`), and
    `text_after`.

    Attributes:
        state: Scanner state after the call.
        text_before: Natural-language text released before the envelope.
        started: Whether this call found the opening delimiter.
        payload_delta: Payload text released by this call.
        completed: Whether this call found the closing delimiter.
        text_after: Natural-language text released after the envelope.
        payload: The complete payload, once the envelope is complete.
    """

    state: EnvelopeState
    text_before: str = ""
    started: bool = False
    payload_delta: str = ""
    completed: bool = False
    text_after: str = ""
    payload: str | None = None


class EnvelopeScanner:
    """Find one envelope in text that arrives in arbitrary chunks.

    Text is released as soon as it can no longer be part of a delimiter, so the
    scanner holds back at most one delimiter's length of input. A closing delimiter
    inside a JSON string does not end the envelope. Text after the envelope is
    released unchanged.

    Args:
        spec: The envelope delimiters. Defaults to ``<xstructured>`` / ``</xstructured>``.
        max_envelope_chars: Maximum envelope length, delimiters included.
        max_payload_chars: Maximum payload length.

    Raises:
        ValueError: If a limit is not positive.
    """

    def __init__(
        self,
        spec: EnvelopeSpec | None = None,
        *,
        max_envelope_chars: int = 1_000_000,
        max_payload_chars: int = 1_000_000,
    ) -> None:
        if max_envelope_chars < 1 or max_payload_chars < 1:
            raise ValueError("Envelope limits must be positive")
        self._spec = spec or EnvelopeSpec()
        self._max_envelope_chars = max_envelope_chars
        self._max_payload_chars = max_payload_chars
        self._state = EnvelopeState.SEEKING_START
        self._buffer = ""
        self._offset = 0
        self._payload_parts: list[str] = []
        self._payload_chars = 0
        self._string_state = OUTSIDE
        self._start_index = 0
        self._payload: str | None = None
        self._span: tuple[int, int] | None = None

    @property
    def spec(self) -> EnvelopeSpec:
        """The envelope delimiters."""
        return self._spec

    @property
    def state(self) -> EnvelopeState:
        """The current scanner state."""
        return self._state

    @property
    def complete(self) -> bool:
        """Whether the closing delimiter has been found."""
        return self._state is EnvelopeState.COMPLETE

    @property
    def payload(self) -> str | None:
        """The complete payload, or ``None`` until the envelope is complete."""
        return self._payload

    @property
    def span(self) -> tuple[int, int] | None:
        """``(start, end)`` offsets of the complete envelope in all text fed so far."""
        return self._span

    def feed(self, chunk: str) -> ScanEvent:
        """Accept the next chunk of text.

        Raises:
            TypeError: If *chunk* is not a string.
            LimitExceededError: If the envelope or its payload exceeds its limit.
        """
        if not isinstance(chunk, str):
            raise TypeError("Envelope scanner chunks must be strings")
        if self._state is EnvelopeState.COMPLETE:
            self._offset += len(chunk)
            return ScanEvent(
                self._state, text_after=chunk, payload=self._payload
            )

        self._buffer += chunk
        text_before = ""
        started = False
        if self._state is EnvelopeState.SEEKING_START:
            start_at = self._buffer.find(self._spec.start)
            if start_at < 0:
                released = max(0, len(self._buffer) - len(self._spec.start) + 1)
                return ScanEvent(self._state, text_before=self._take(released))
            text_before = self._take(start_at)
            self._start_index = self._offset
            self._take(len(self._spec.start))
            self._state = EnvelopeState.COLLECTING
            started = True

        scan = scan_for_delimiter(
            self._buffer, self._spec.end, state=self._string_state
        )
        if scan.index < 0:
            delta = self._take(scan.position)
            self._string_state = scan.state
            self._append_payload(delta)
            self._check_envelope(pending=len(self._buffer))
            return ScanEvent(
                self._state,
                text_before=text_before,
                started=started,
                payload_delta=delta,
            )

        delta = self._take(scan.index)
        self._append_payload(delta)
        self._check_envelope(pending=len(self._spec.end))
        self._take(len(self._spec.end))
        self._payload = "".join(self._payload_parts)
        self._span = (self._start_index, self._offset)
        self._state = EnvelopeState.COMPLETE
        return ScanEvent(
            self._state,
            text_before=text_before,
            started=started,
            payload_delta=delta,
            completed=True,
            text_after=self._take(len(self._buffer)),
            payload=self._payload,
        )

    def finalize(self) -> ScanEvent:
        """Release any text held back at the end of the input.

        The scanner state is left unchanged, so `complete` still reports whether a
        complete envelope was found.

        Raises:
            LimitExceededError: If the released payload text exceeds the payload limit.
        """
        rest = self._take(len(self._buffer))
        if self._state is EnvelopeState.SEEKING_START:
            return ScanEvent(self._state, text_before=rest)
        if self._state is EnvelopeState.COLLECTING:
            self._append_payload(rest)
            return ScanEvent(self._state, payload_delta=rest)
        return ScanEvent(self._state, payload=self._payload)

    @property
    def _partial_text(self) -> str:
        return self._spec.start + "".join(self._payload_parts)

    def _append_payload(self, text: str) -> None:
        if not text:
            return
        self._payload_parts.append(text)
        self._payload_chars += len(text)
        if self._payload_chars > self._max_payload_chars:
            raise LimitExceededError(
                f"Envelope payload exceeds the configured limit of "
                f"{self._max_payload_chars} characters",
                text=self._partial_text,
                limit="max_payload_chars",
                maximum=self._max_payload_chars,
            )

    def _check_envelope(self, *, pending: int) -> None:
        size = len(self._spec.start) + self._payload_chars + pending
        if size > self._max_envelope_chars:
            raise LimitExceededError(
                f"Envelope exceeds the configured limit of {self._max_envelope_chars} characters",
                text=self._partial_text,
                limit="max_envelope_chars",
                maximum=self._max_envelope_chars,
            )

    def _take(self, length: int) -> str:
        value = self._buffer[:length]
        self._buffer = self._buffer[length:]
        self._offset += len(value)
        return value
