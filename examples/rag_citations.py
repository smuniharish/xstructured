"""Answer from retrieved documents with validated citations.

The schema requires at least one citation, and a post-validation check
confirms that every citation points at a retrieved document and quotes it
verbatim.

Run it with ``uv run python examples/rag_citations.py``.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from _shared import banner, chat_model
from xstructured import with_xstructured_output

DOCUMENTS = {
    "runbook-17": (
        "Deploys use canary traffic for ten minutes before full rollout."
    ),
    "policy-4": "Production changes require an approved change record.",
}
SCRIPTED_REPLY = (
    "Two requirements apply before a production rollout.\n"
    "<xstructured>"
    '{"answer": "You need an approved change record, and the deploy must run '
    'on canary traffic for ten minutes before full rollout.", "citations": ['
    '{"source_id": "policy-4", '
    '"quote": "Production changes require an approved change record."}, '
    '{"source_id": "runbook-17", '
    '"quote": "Deploys use canary traffic for ten minutes before full '
    'rollout."}]}'
    "</xstructured>"
)


class Citation(BaseModel):
    """A verbatim quote from one retrieved document."""

    source_id: str
    quote: str


class CitedAnswer(BaseModel):
    """An answer whose claims are backed by retrieved documents."""

    answer: str
    citations: list[Citation] = Field(min_length=1)


def main() -> None:
    context = "\n".join(
        f"[{source}] {text}" for source, text in DOCUMENTS.items()
    )
    question = "What is required before a production rollout?"
    result = with_xstructured_output(
        chat_model(SCRIPTED_REPLY), CitedAnswer
    ).invoke(
        [
            HumanMessage(
                "Answer using only these documents. Cite every claim with its "
                f"source_id and a verbatim quote.\n\n{context}\n\n"
                f"Question: {question}"
            )
        ]
    )

    banner("RAG answer with citations")
    print(f"Answer: {result.structured.answer}")
    for citation in result.structured.citations:
        verified = citation.quote in DOCUMENTS.get(citation.source_id, "")
        print(f"[{citation.source_id}] {citation.quote} (verified: {verified})")


if __name__ == "__main__":
    main()
