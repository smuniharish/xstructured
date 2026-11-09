"""An observer to copy into a project and point at a metrics backend.

`MetricsObserver` counts calls by operation and outcome and records parse
durations and response sizes. It keeps them in memory; replace the three
`_record_*` methods with calls to your backend (Prometheus, StatsD, Datadog,
CloudWatch). Attributes never contain prompt or response text.

Rules every observer keeps:

- `start` returns a new `Observation` for each call and does no I/O that can
  block the event loop; buffer and flush in the background instead.
- The observation is finished exactly once, with `succeed` or `fail`.
- `fail` receives cancellations too (`asyncio.CancelledError`,
  `GeneratorExit`); count them separately from errors.
- Never raise from `succeed` or `fail`: a broken metrics backend must not
  fail the caller's request.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections import Counter
from collections.abc import Mapping
from typing import override

from xstructured import AttributeValue, Observation, Observer

log = logging.getLogger(__name__)
CANCELLATIONS = (asyncio.CancelledError, GeneratorExit, KeyboardInterrupt)


class MetricsObserver(Observer):
    """Count xstructured calls and record their sizes and durations."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.calls: Counter[tuple[str, str]] = Counter()
        self.durations: list[float] = []
        self.response_chars: list[int] = []

    @override
    def start(
        self, operation: str, attributes: Mapping[str, AttributeValue]
    ) -> Observation:
        return _CallObservation(self, operation)

    def _record_call(self, operation: str, outcome: str) -> None:
        with self._lock:
            self.calls[operation, outcome] += 1

    def _record_duration(self, seconds: float) -> None:
        with self._lock:
            self.durations.append(seconds)

    def _record_size(self, chars: int) -> None:
        with self._lock:
            self.response_chars.append(chars)


class _CallObservation(Observation):
    def __init__(self, observer: MetricsObserver, operation: str) -> None:
        self._observer = observer
        self._operation = operation
        self._finished = False

    @override
    def succeed(self, attributes: Mapping[str, AttributeValue]) -> None:
        if self._finish():
            try:
                outcome = (
                    "repaired"
                    if attributes.get("xstructured.repaired")
                    else "ok"
                )
                self._observer._record_call(self._operation, outcome)  # noqa: SLF001
                duration = attributes.get("xstructured.parse_duration")
                if isinstance(duration, float):
                    self._observer._record_duration(duration)  # noqa: SLF001
                chars = attributes.get("xstructured.response_chars")
                if isinstance(chars, int):
                    self._observer._record_size(chars)  # noqa: SLF001
            except Exception:  # never fail the caller because of metrics
                log.exception("xstructured metrics could not be recorded")

    @override
    def fail(self, error: BaseException) -> None:
        if self._finish():
            outcome = (
                "cancelled" if isinstance(error, CANCELLATIONS) else "error"
            )
            try:
                self._observer._record_call(self._operation, outcome)  # noqa: SLF001
            except Exception:  # never fail the caller because of metrics
                log.exception("xstructured metrics could not be recorded")

    def _finish(self) -> bool:
        if self._finished:
            return False
        self._finished = True
        return True
