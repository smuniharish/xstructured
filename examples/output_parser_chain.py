"""Parse a prompt-template chain's output with ``XStructuredOutputParser``.

The parser is an ordinary LangChain output parser: put its format
instructions in the prompt and add it to the end of an LCEL chain. A
validation context set in the run config reaches the schema's validators, so
one chain serves tenants with different rules.

Run it with ``uv run python examples/output_parser_chain.py``.
"""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ValidationInfo, field_validator

from _shared import banner, chat_model
from xstructured import CONTEXT_KEY, XStructuredOutputParser

SCRIPTED_REPLY = (
    "The invoice is from Northwind and is payable in euros.\n"
    "<xstructured>"
    '{"vendor": "Northwind Traders", "total": 1280.5, "currency": "EUR"}'
    "</xstructured>"
)


class Invoice(BaseModel):
    """The fields an accounts-payable team needs."""

    vendor: str
    total: float
    currency: str

    @field_validator("currency")
    @classmethod
    def accepted_currency(cls, value: str, info: ValidationInfo) -> str:
        """Reject currencies the caller's context does not accept."""
        accepted = (info.context or {}).get("currencies")
        if accepted is not None and value not in accepted:
            raise ValueError(f"currency must be one of {sorted(accepted)}")
        return value


async def main() -> None:
    parser = XStructuredOutputParser(Invoice)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You read invoices.\n\n{format_instructions}"),
            ("human", "{invoice}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())
    config: Any = {"configurable": {CONTEXT_KEY: {"currencies": {"EUR"}}}}

    async with chat_model(SCRIPTED_REPLY) as model:
        chain = prompt | model | parser
        result = await chain.ainvoke(
            {
                "invoice": "Northwind Traders, invoice 2026-114: consulting, "
                "EUR 1,280.50 due in 30 days. Summarize it in one sentence."
            },
            config,
        )

    banner("Output parser in an LCEL chain")
    print(f"Invoice: {result.structured!r}")
    print(f"Summary: {result.content.strip()}")


if __name__ == "__main__":
    asyncio.run(main())
