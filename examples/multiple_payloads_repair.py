"""Multiple structured payloads with an optional real-LLM repair fallback.

This example uses the OpenAI-compatible Experiential Labs endpoint for both
the primary response and the opt-in repair response. Repair is only called if
the primary response cannot be parsed and validated.

Requires EXPLABS_API_KEY. Install the example dependencies first:

    uv sync --group examples
    $env:EXPLABS_API_KEY = "..."
    uv run python examples/multiple_payloads_repair.py
"""

from __future__ import annotations

from _shared import explabs_chat_model, print_result_header, require_env, require_package

require_package("langchain_openai", extra_group="examples")
require_env("EXPLABS_API_KEY")

from pydantic import BaseModel, Field  # noqa: E402

from xstructured import RepairConfig, with_xstructured_output  # noqa: E402


class Finding(BaseModel):
    """A finding extracted from a report."""

    title: str
    severity: str
    evidence: str


class Action(BaseModel):
    """A follow-up action extracted from a report."""

    owner: str
    action: str
    priority: str = Field(pattern="^(high|medium|low)$")


def main() -> None:
    model = explabs_chat_model()
    chain = with_xstructured_output(
        model,
        {"finding": Finding, "action": Action},
        multiple=True,
        repair=model,
        repair_config=RepairConfig(max_attempts=2),
    )
    result = chain.invoke(
        "Review this incident report and return every finding and follow-up action. "
        "Use one xstructured envelope containing an array. Each array item must be "
        "tagged with schema='finding' or schema='action'. Include concise evidence "
        "for findings and an owner for actions. "
        "Report: checkout failures rose after the release; rollback reduced errors; "
        "add a canary check before the next deployment."
    )

    print_result_header("Multiple payloads with LLM-assisted repair")
    print(f"Validated payload count: {len(result.structured)}")
    for item in result.structured:
        print(f"- {item!r}")
    print(f"Repair attempted: {result.repaired}")


if __name__ == "__main__":
    main()
