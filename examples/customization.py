"""Customize the instructions, validation, and telemetry of a wrapper.

Every extension point is an abstract base class with a default
implementation:

- An ``InstructionRenderer`` subclass adds a house-style rule to the
  instructions sent to the model.
- ``SchemaOptions`` forwards Pydantic options; here unknown fields are
  rejected.
- An ``Observer`` subclass receives sizes, counts, and flags for every call,
  never prompt or response text, so it can feed any metrics backend.

Run it with ``uv run python examples/customization.py``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any, override

from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from _shared import banner, chat_model
from xstructured import (
    AttributeValue,
    DefaultInstructionRenderer,
    EnvelopeSpec,
    NamedSchemas,
    Observation,
    Observer,
    SchemaInfo,
    SchemaOptions,
    with_xstructured_output,
)

SCRIPTED_REPLY = (
    "Meeting booked for the platform review.\n"
    "<xstructured>"
    '{"title": "Platform review", "date": "2026-11-03", "attendees": 4}'
    "</xstructured>"
)


class Meeting(BaseModel):
    """A calendar entry."""

    title: str
    date: str
    attendees: int


class HouseStyleRenderer(DefaultInstructionRenderer):
    """The default instructions plus one organization-wide rule."""

    @override
    def render(
        self,
        schema: SchemaInfo | NamedSchemas | Mapping[str, Any],
        *,
        envelope: EnvelopeSpec | None,
        multiple: bool,
        multiple_envelopes: bool,
    ) -> str:
        instructions = super().render(
            schema,
            envelope=envelope,
            multiple=multiple,
            multiple_envelopes=multiple_envelopes,
        )
        return f"{instructions}\n\nWrite every date as YYYY-MM-DD."


class PrintedObservation(Observation):
    """Prints one line when the call finishes."""

    def __init__(self, operation: str) -> None:
        self.operation = operation

    @override
    def succeed(self, attributes: Mapping[str, AttributeValue]) -> None:
        print(
            f"[metrics] {self.operation} ok: "
            f"recovered={attributes['xstructured.recovered']} "
            f"envelopes={attributes['xstructured.envelope_count']} "
            f"response_chars={attributes['xstructured.response_chars']}"
        )

    @override
    def fail(self, error: BaseException) -> None:
        print(f"[metrics] {self.operation} failed: {type(error).__name__}")


class PrintedMetrics(Observer):
    """An observer that prints a metrics line per call."""

    @override
    def start(
        self, operation: str, attributes: Mapping[str, AttributeValue]
    ) -> Observation:
        return PrintedObservation(operation)


async def main() -> None:
    banner("Customized wrapper")
    async with chat_model(SCRIPTED_REPLY) as model:
        scheduler = with_xstructured_output(
            model,
            Meeting,
            renderer=HouseStyleRenderer(),
            schema_options=SchemaOptions(extra="forbid"),
            observer=PrintedMetrics(),
            name="scheduler",
        )
        result = await scheduler.ainvoke(
            [
                HumanMessage(
                    "Book the platform review on November 3rd, 2026 for four "
                    "people and confirm in one sentence."
                )
            ]
        )

    print(f"Meeting: {result.structured!r}")
    print(f"House rule sent: {scheduler.instructions.endswith('YYYY-MM-DD.')}")


if __name__ == "__main__":
    asyncio.run(main())
