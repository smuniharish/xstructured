"""Turn an operator's incident report into a structured action plan.

Run it with ``uv run python examples/incident_analysis.py``.
"""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from _shared import banner, chat_model
from xstructured import with_xstructured_output

SCRIPTED_REPLY = (
    "The rollback points to the release as the trigger; the root cause "
    "still needs review.\n"
    "<xstructured>"
    '{"severity": "high", '
    '"summary": "Checkout errors rose to 35% after release '
    '2026.09.18; rolling back reduced them to 1% within five minutes.", '
    '"probable_cause": "A regression introduced by release 2026.09.18.", '
    '"immediate_actions": ["Keep the rollback in place", '
    '"Watch checkout error rates"], '
    '"follow_up_actions": ["Bisect the release for the failing change", '
    '"Add a checkout canary before the next deploy"]}'
    "</xstructured>"
)


class IncidentAnalysis(BaseModel):
    """Fields for an incident ticket and hand-off."""

    severity: Literal["low", "medium", "high", "critical"]
    summary: str
    probable_cause: str
    immediate_actions: list[str] = Field(min_length=1)
    follow_up_actions: list[str] = Field(min_length=1)


def main() -> None:
    report = (
        "At 09:12 UTC checkout errors rose to 35% after release 2026.09.18. "
        "Rolling back reduced errors to 1% within five minutes. "
        "Explain your assessment in one sentence before the structured block."
    )
    result = with_xstructured_output(
        chat_model(SCRIPTED_REPLY), IncidentAnalysis
    ).invoke([HumanMessage(report)])

    banner("Incident analysis")
    analysis = result.structured
    print(f"Severity:       {analysis.severity}")
    print(f"Summary:        {analysis.summary}")
    print(f"Probable cause: {analysis.probable_cause}")
    print(f"Immediate:      {analysis.immediate_actions}")
    print(f"Follow-up:      {analysis.follow_up_actions}")
    print(f"Explanation:    {result.content.strip()}")


if __name__ == "__main__":
    main()
