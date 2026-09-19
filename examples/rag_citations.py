"""RAG-style answer generation with explicit, validated citations."""

from __future__ import annotations

from _shared import explabs_chat_model, print_result_header, require_env, require_package

require_package("langchain", extra_group="examples")
require_env("EXPLABS_API_KEY")

from langchain_core.messages import HumanMessage  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from xstructured import with_xstructured_output  # noqa: E402


class Citation(BaseModel):
    """A citation pointing at one retrieved document."""

    source_id: str
    quote: str


class CitedAnswer(BaseModel):
    """An answer whose claims can be checked against retrieved context."""

    answer: str
    citations: list[Citation] = Field(min_length=1)


DOCUMENTS = {
    "runbook-17": "Deploys use canary traffic for ten minutes before full rollout.",
    "policy-4": "Production changes require an approved change record.",
}


def main() -> None:
    context = "\n".join(f"[{key}] {value}" for key, value in DOCUMENTS.items())
    prompt = (
        "Answer the question using only the retrieved documents. Cite every important claim "
        "with a source_id and a short verbatim quote.\n\n"
        "Retrieved documents:\n"
        f"{context}\n\nQuestion: What is required before a production rollout?"
    )
    result = with_xstructured_output(explabs_chat_model(), CitedAnswer).invoke(
        [HumanMessage(content=prompt)]
    )
    print_result_header("RAG answer with citations")
    print(f"Answer: {result.structured.answer}")
    for citation in result.structured.citations:
        print(f"[{citation.source_id}] {citation.quote}")


if __name__ == "__main__":
    main()
