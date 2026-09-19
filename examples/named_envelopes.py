"""Multiple separately named structured envelopes in one model response."""

from __future__ import annotations

from _shared import explabs_chat_model, print_result_header, require_env, require_package

require_package("langchain_openai", extra_group="examples")
require_env("EXPLABS_API_KEY")

from pydantic import BaseModel  # noqa: E402

from xstructured import with_xstructured_output  # noqa: E402


class Finding(BaseModel):
    title: str
    severity: str


class Recommendation(BaseModel):
    owner: str
    action: str


def main() -> None:
    chain = with_xstructured_output(
        explabs_chat_model(),
        {"finding": Finding, "recommendation": Recommendation},
        multiple_envelopes=True,
    )
    result = chain.invoke(
        "Analyze the checkout incident. Return separate named xstructured envelopes "
        "for finding and recommendation."
    )
    print_result_header("Multiple named envelopes")
    print(f"Finding: {result.structured['finding']!r}")
    print(f"Recommendation: {result.structured['recommendation']!r}")


if __name__ == "__main__":
    main()
