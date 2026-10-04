"""Validate several typed payloads from one response, with bounded LLM repair.

The response carries one JSON array whose items are tagged with a schema
name, so a single reply can mix ``Finding`` and ``Action`` values. If the
response is invalid, a repair model is asked to correct it, at most twice. In
offline mode the scripted first reply contains invalid JSON, so repair runs.

Run it with ``uv run python examples/multiple_payloads_repair.py``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from _shared import banner, chat_model, is_live
from xstructured import RepairConfig, with_xstructured_output

INVALID_REPLY = (
    "Two findings and one action.\n"
    "<xstructured>[{schema: 'finding', payload: {title: 'Checkout errors'}}]"
    "</xstructured>"
)
REPAIRED_REPLY = (
    "<xstructured>["
    '{"schema": "finding", "payload": '
    '{"title": "Checkout failures rose after the release", '
    '"severity": "high"}},'
    '{"schema": "finding", "payload": '
    '{"title": "Rollback restored the error rate", "severity": "medium"}},'
    '{"schema": "action", "payload": {"owner": "release-engineering", '
    '"action": "Add a checkout canary before the next deploy", '
    '"priority": "high"}}'
    "]</xstructured>"
)


class Finding(BaseModel):
    """Something observed in the incident."""

    title: str
    severity: Literal["low", "medium", "high"]


class Action(BaseModel):
    """A follow-up task."""

    owner: str
    action: str
    priority: Literal["low", "medium", "high"]


def main() -> None:
    model = chat_model(INVALID_REPLY)
    chain = with_xstructured_output(
        model,
        {"finding": Finding, "action": Action},
        multiple=True,
        repair=model if is_live() else chat_model(REPAIRED_REPLY),
        repair_config=RepairConfig(max_attempts=2),
    )
    result = chain.invoke(
        "Review this incident: checkout failures rose after the release, a "
        "rollback restored the error rate, and a canary check should be "
        "added before the next deploy."
    )

    banner("Multiple payloads with bounded repair")
    for item in result.structured:
        print(f"- {item!r}")
    print(f"Repaired: {result.repaired} (attempts: {result.repair_attempts})")


if __name__ == "__main__":
    main()
