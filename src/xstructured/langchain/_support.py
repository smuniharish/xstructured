"""Internal helpers shared by the LangChain integration modules."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage


def output_text(output: Any) -> str:
    """Extract the text content of a wrapped or repair Runnable's raw output."""
    if isinstance(output, str):
        return output
    if isinstance(output, BaseMessage):
        return output.text
    raise TypeError(
        "The wrapped Runnable must return strings or LangChain "
        f"BaseMessage values, not {type(output).__name__}"
    )
