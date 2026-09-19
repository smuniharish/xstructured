"""Optional, bounded LLM-assisted repair for otherwise-unparseable output.

Recovery (`xstructured.core.RecoveryConfig`) only ever changes which
substring of a response is treated as JSON; it never rewrites syntax (see
ADR 0003). Repair is a separate, strictly opt-in escape hatch: it only runs
when the caller supplies a *repair* `Runnable` to `with_xstructured_output`,
and it is bounded by `RepairConfig.max_attempts` so it can never loop
indefinitely. Every repaired response is re-validated by the same
`StructuredParser` -- the same schema(s) and the same recovery rules -- as
the original response, so repair can change what an *invalid* response was,
but never weaken what counts as *valid*.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Generic, TypeVar

from langchain_core.runnables import Runnable, RunnableConfig

from xstructured.core import ParseError, ParseResult, RecoveryError, RepairConfig, RepairError
from xstructured.parser import StructuredParser

from ._support import output_text

T = TypeVar("T")

_REPAIR_PREAMBLE = (
    "The following response failed schema validation and must be corrected. "
    "Return only a corrected response; do not add commentary or explanation."
)


class Repairer(Generic[T]):
    """Bounded, opt-in retry loop that asks a Runnable to fix invalid output."""

    def __init__(
        self,
        parser: StructuredParser[T],
        repair_runnable: Runnable[Any, Any],
        config: RepairConfig,
        instructions: str,
    ) -> None:
        self._parser = parser
        self._repair_runnable = repair_runnable
        self._config = config
        self._instructions = instructions

    def repair(
        self,
        text: str,
        error: ParseError,
        *,
        config: RunnableConfig | None = None,
    ) -> ParseResult[T]:
        """Synchronously retry parsing, invoking the repair Runnable each attempt."""
        if not self._config.enabled:
            raise error
        current_text, current_error = text, error
        for attempt in range(1, self._config.max_attempts + 1):
            prompt = self._build_prompt(current_text, current_error, attempt)
            response = self._repair_runnable.invoke(prompt, config=config)
            current_text = output_text(response)
            try:
                return replace(
                    self._parser.parse(current_text),
                    repaired=True,
                    repair_attempt_count=attempt,
                )
            except ParseError as new_error:
                current_error = new_error
        raise self._exhausted(current_error)

    async def arepair(
        self,
        text: str,
        error: ParseError,
        *,
        config: RunnableConfig | None = None,
    ) -> ParseResult[T]:
        """Asynchronously retry parsing, invoking the repair Runnable each attempt."""
        if not self._config.enabled:
            raise error
        current_text, current_error = text, error
        for attempt in range(1, self._config.max_attempts + 1):
            prompt = self._build_prompt(current_text, current_error, attempt)
            response = await self._repair_runnable.ainvoke(prompt, config=config)
            current_text = output_text(response)
            try:
                return replace(
                    self._parser.parse(current_text),
                    repaired=True,
                    repair_attempt_count=attempt,
                )
            except ParseError as new_error:
                current_error = new_error
        raise self._exhausted(current_error)

    def _build_prompt(self, text: str, error: ParseError, attempt: int) -> str:
        messages = _error_messages(error)
        lines = [
            _REPAIR_PREAMBLE,
            "",
            self._instructions,
            "",
            f"Repair attempt {attempt} of {self._config.max_attempts}.",
            "Validation errors:",
            *(f"- {message}" for message in messages),
            "",
            "Invalid response:",
            text,
        ]
        return "\n".join(lines)

    def _exhausted(self, error: ParseError) -> RepairError:
        return RepairError(
            "LLM-assisted repair did not produce schema-valid output within "
            f"the configured attempt budget ({self._config.max_attempts})",
            error.text,
            error,
            attempt_count=self._config.max_attempts,
            repair_errors=_error_messages(error),
        )


def _error_messages(error: ParseError) -> tuple[str, ...]:
    if isinstance(error, RecoveryError) and error.attempts:
        return error.attempts
    return (str(error),)
