"""Message helpers for the LangChain integration."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.messages import (
    BaseMessage,
    BaseMessageChunk,
    SystemMessage,
    convert_to_messages,
    message_chunk_to_message,
)
from langchain_core.prompt_values import ChatPromptValue, PromptValue

__all__ = ["ChunkAccumulator", "inject_instructions", "output_text"]

_UNSUPPORTED_INPUT = (
    "Cannot add xstructured instructions to input of type {type_name}. Pass a string, a "
    "PromptValue, or a sequence of messages, or create the wrapper with "
    "inject_instructions=False and include its `instructions` in your prompt."
)


def output_text(output: Any) -> str:
    """Return the text of a wrapped Runnable's output (a string or a message).

    Raises:
        TypeError: If *output* is neither a string nor a `BaseMessage`.
    """
    if isinstance(output, str):
        return output
    if isinstance(output, BaseMessage):
        return output.text
    raise TypeError(
        f"The wrapped Runnable must return str or BaseMessage values, not {type(output).__name__}"
    )


class ChunkAccumulator:
    """Collect streamed output chunks and their text."""

    def __init__(self) -> None:
        self._chunks: list[Any] = []
        self._parts: list[str] = []

    @property
    def text(self) -> str:
        """The concatenated text of all chunks."""
        return "".join(self._parts)

    def add(self, chunk: Any) -> str:
        """Record *chunk* and return its text."""
        text = output_text(chunk)
        self._chunks.append(chunk)
        self._parts.append(text)
        return text

    def output(self) -> Any:
        """The merged output: one message for message chunks, one string for strings."""
        chunks = self._chunks
        if all(isinstance(chunk, str) for chunk in chunks):
            return "".join(chunks)
        messages = [
            chunk for chunk in chunks if isinstance(chunk, BaseMessageChunk)
        ]
        if len(messages) == len(chunks):
            merged = messages[0]
            for message in messages[1:]:
                merged += message
            return message_chunk_to_message(merged)
        if len(chunks) == 1:
            return chunks[0]
        return tuple(chunks)


def inject_instructions(value: Any, instructions: str) -> Any:
    """Add *instructions* to a model input.

    Strings get the instructions appended. Prompt values and message sequences get them
    as a system message: appended to a leading system message when there is one,
    otherwise prepended as a new one.

    Raises:
        TypeError: If the input type cannot carry instructions.
    """
    if isinstance(value, str):
        return f"{value}\n\n{instructions}"
    if isinstance(value, PromptValue):
        return ChatPromptValue(
            messages=_with_instructions(value.to_messages(), instructions)
        )
    if isinstance(value, Sequence) and not isinstance(
        value, (bytes, bytearray)
    ):
        try:
            messages = convert_to_messages(value)
        except (KeyError, NotImplementedError, TypeError, ValueError) as exc:
            raise TypeError(
                _UNSUPPORTED_INPUT.format(type_name=type(value).__name__)
            ) from exc
        return _with_instructions(messages, instructions)
    raise TypeError(_UNSUPPORTED_INPUT.format(type_name=type(value).__name__))


def _with_instructions(
    messages: list[BaseMessage], instructions: str
) -> list[BaseMessage]:
    if messages and isinstance(messages[0], SystemMessage):
        first = messages[0]
        content = first.content
        merged: str | list[str | dict[str, Any]] = (
            (f"{content}\n\n{instructions}" if content else instructions)
            if isinstance(content, str)
            else [*content, {"type": "text", "text": instructions}]
        )
        return [first.model_copy(update={"content": merged}), *messages[1:]]
    return [SystemMessage(content=instructions), *messages]
