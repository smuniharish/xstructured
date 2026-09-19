"""Stream xstructured events to a terminal UI (or adapt them to web SSE)."""

from __future__ import annotations

from _shared import explabs_chat_model, print_result_header, require_env, require_package

require_package("langchain", extra_group="examples")
require_env("EXPLABS_API_KEY")

from langchain_core.messages import HumanMessage  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from xstructured import StreamEventKind, with_xstructured_output  # noqa: E402


class StatusUpdate(BaseModel):
    """A structured status payload that a UI can render as a card."""

    status: str
    next_step: str


def main() -> None:
    stream = with_xstructured_output(explabs_chat_model(), StatusUpdate).stream(
        [HumanMessage(content="Report the deployment status and next step.")]
    )
    print_result_header("Streaming UI events")
    for event in stream:
        if event.kind is StreamEventKind.TEXT_DELTA:
            print(event.text or "", end="", flush=True)
        else:
            print(f"\n[event={event.kind} sequence={event.sequence}]")
            if event.kind is StreamEventKind.RESULT:
                print(f"structured={event.result.structured!r}")
    print()


if __name__ == "__main__":
    main()
