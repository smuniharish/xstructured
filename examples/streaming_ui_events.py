"""Stream prose and structured data as ordered events for a UI or SSE adapter.

Text deltas can be shown immediately; the structured value becomes available
when the envelope closes, and the final ``RESULT`` event carries the complete
result.

Run it with ``uv run python examples/streaming_ui_events.py``.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from _shared import banner, chat_model
from xstructured import StreamEventKind, with_xstructured_output

SCRIPTED_REPLY = (
    "The deployment finished and all health checks are green. "
    '<xstructured>{"status": "healthy", '
    '"next_step": "Promote the release to all regions."}'
    "</xstructured> I will keep monitoring for the next hour."
)


class StatusUpdate(BaseModel):
    """A status card for a dashboard."""

    status: str
    next_step: str


def main() -> None:
    events = with_xstructured_output(
        chat_model(SCRIPTED_REPLY), StatusUpdate
    ).stream(
        [
            HumanMessage(
                "Deployment 2026.10.04-1 finished at 14:02 UTC. All 12 health "
                "checks pass in eu-west and us-east, and error rates are at "
                "baseline. Tell the user the status in one sentence, then give "
                "the status card."
            )
        ]
    )

    banner("Streaming UI events")
    deltas = 0
    for event in events:
        match event.kind:
            case StreamEventKind.TEXT_DELTA:
                print(event.text or "", end="", flush=True)
            case StreamEventKind.STRUCTURED_DELTA:
                deltas += 1
            case StreamEventKind.STRUCTURED_END:
                print(
                    f"\n[card ready after {deltas} structured deltas] "
                    f"{event.structured!r}"
                )
            case StreamEventKind.RESULT if event.result is not None:
                print(
                    f"\n[result #{event.sequence}] "
                    f"recovered={event.result.recovered}"
                )
            case _:
                pass


if __name__ == "__main__":
    main()
