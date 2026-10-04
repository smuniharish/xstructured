"""Read separately named envelopes, each validated against its own schema.

Run it with ``uv run python examples/named_envelopes.py``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from _shared import banner, chat_model
from xstructured import with_xstructured_output

SCRIPTED_REPLY = (
    "Analysis: the error spike started with the 09:10 release.\n"
    '<xstructured name="finding">'
    '{"title": "Checkout regression in release 2026.09.18", "severity": "high"}'
    "</xstructured>\n"
    "Recommendation: keep the rollback and add a guard rail.\n"
    '<xstructured name="recommendation">'
    '{"owner": "platform", '
    '"action": "Add a checkout canary to the deploy pipeline"}'
    "</xstructured>"
)


class Finding(BaseModel):
    """What went wrong."""

    title: str
    severity: Literal["low", "medium", "high"]


class Recommendation(BaseModel):
    """What to do next."""

    owner: str
    action: str


def main() -> None:
    chain = with_xstructured_output(
        chat_model(SCRIPTED_REPLY),
        {"finding": Finding, "recommendation": Recommendation},
        multiple_envelopes=True,
    )
    result = chain.invoke(
        "Incident report: release 2026.09.18 went out at 09:10 UTC. From "
        "09:12, checkout errors rose to 35% for card payments only; rolling "
        "back at 09:20 restored the baseline within five minutes. The release "
        "changed the payment-provider client. Write a short analysis, then "
        "give one finding and one recommendation."
    )

    banner("Multiple named envelopes")
    for name, value in result.structured.items():
        print(f"{name}: {value!r}")
    print(f"Prose: {result.content.strip()!r}")


if __name__ == "__main__":
    main()
