"""Opt-in, bounded LLM-assisted repair.

Repair runs only when a repair Runnable is configured and conservative recovery has
failed. Each repaired response is parsed by the same `StructuredParser` as the original
response, so repair can only replace an invalid response; it never relaxes validation.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from langchain_core.runnables import Runnable, RunnableConfig

from xstructured.core.config import RepairConfig
from xstructured.core.errors import ParseError, RecoveryError, RepairError
from xstructured.core.result import ParseResult
from xstructured.parser.parser import StructuredParser

from ._messages import output_text

__all__ = ["Repairer"]


class Repairer[T]:
    """Ask a Runnable to correct an invalid response, within an attempt budget."""

    def __init__(
        self,
        parser: StructuredParser[T],
        runnable: Runnable[Any, Any],
        config: RepairConfig,
        instructions: str,
    ) -> None:
        self._parser = parser
        self._runnable = runnable
        self._config = config
        self._instructions = instructions

    @property
    def enabled(self) -> bool:
        """Whether repair may run."""
        return self._config.enabled

    def repair(
        self, text: str, error: ParseError, config: RunnableConfig
    ) -> ParseResult[T]:
        """Repair *text*, which failed with *error*.

        Raises:
            RepairError: If no attempt produced a valid response.
        """
        failures: list[str] = []
        current_text, current_error = text, error
        for attempt in range(1, self._config.max_attempts + 1):
            response = self._runnable.invoke(
                self._prompt(current_text, current_error, attempt), config
            )
            current_text = output_text(response)
            try:
                parsed = self._parser.parse(current_text)
            except ParseError as exc:
                failures.append(str(exc))
                current_error = exc
                continue
            return replace(parsed, repaired=True, repair_attempts=attempt)
        raise self._exhausted(text, failures) from current_error

    async def arepair(
        self, text: str, error: ParseError, config: RunnableConfig
    ) -> ParseResult[T]:
        """Asynchronously repair *text*, which failed with *error*.

        Raises:
            RepairError: If no attempt produced a valid response.
        """
        failures: list[str] = []
        current_text, current_error = text, error
        for attempt in range(1, self._config.max_attempts + 1):
            response = await self._runnable.ainvoke(
                self._prompt(current_text, current_error, attempt), config
            )
            current_text = output_text(response)
            try:
                parsed = self._parser.parse(current_text)
            except ParseError as exc:
                failures.append(str(exc))
                current_error = exc
                continue
            return replace(parsed, repaired=True, repair_attempts=attempt)
        raise self._exhausted(text, failures) from current_error

    def _prompt(self, text: str, error: ParseError, attempt: int) -> str:
        problems = (
            error.failures
            if isinstance(error, RecoveryError)
            else (str(error),)
        )
        unique = dict.fromkeys(problems)
        return "\n".join(
            [
                (
                    "The response below could not be used because it does not follow the "
                    "required format. Rewrite the complete response so that it follows the "
                    "instructions exactly. Return only the corrected response."
                ),
                "",
                "Instructions:",
                self._instructions,
                "",
                f"Problems (attempt {attempt} of {self._config.max_attempts}):",
                *(f"- {problem}" for problem in unique),
                "",
                "Response to correct:",
                text,
            ]
        )

    def _exhausted(self, text: str, failures: list[str]) -> RepairError:
        attempts = self._config.max_attempts
        return RepairError(
            f"LLM-assisted repair did not produce a valid response in {attempts} attempt(s)",
            text=text,
            attempts=attempts,
            failures=tuple(failures),
        )
