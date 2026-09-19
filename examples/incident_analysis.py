"""Incident analysis that turns an operator report into an action plan."""

from __future__ import annotations

from _shared import explabs_chat_model, print_result_header, require_env, require_package

require_package("langchain", extra_group="examples")
require_env("EXPLABS_API_KEY")

from langchain_core.messages import HumanMessage  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from xstructured import with_xstructured_output  # noqa: E402


class IncidentAnalysis(BaseModel):
    """Structured fields useful for an incident ticket and handoff."""

    severity: str
    summary: str
    probable_cause: str
    immediate_actions: list[str] = Field(min_length=1)
    follow_up_actions: list[str] = Field(min_length=1)


def main() -> None:
    report = (
        "At 09:12 UTC checkout errors rose to 35% after release 2026.09.18. "
        "Rolling back reduced errors to 1% within five minutes."
    )
    result = with_xstructured_output(explabs_chat_model(), IncidentAnalysis).invoke(
        [HumanMessage(content=report)]
    )
    print_result_header("Incident analysis")
    print(f"Severity: {result.structured.severity}")
    print(f"Summary: {result.structured.summary}")
    print(f"Probable cause: {result.structured.probable_cause}")
    print(f"Immediate actions: {result.structured.immediate_actions}")
    print(f"Follow-up actions: {result.structured.follow_up_actions}")


if __name__ == "__main__":
    main()
