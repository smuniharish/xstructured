"""Default instruction injector and output text extractor for LangChain values."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, override

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    BaseMessageChunk,
    SystemMessage,
    convert_to_messages,
    message_chunk_to_message,
)
from langchain_core.prompt_values import ChatPromptValue, PromptValue

from xstructured.contracts import InstructionInjector, OutputTextExtractor

__all__ = [
    "INSTRUCTIONS_MESSAGE_ID",
    "ChunkAccumulator",
    "MessageInstructionInjector",
    "MessageTextExtractor",
    "with_system_instructions",
]

_MESSAGE_TUPLE_LENGTH = 2

INSTRUCTIONS_MESSAGE_ID = "xstructured-instructions"
"""ID of the system message added to LangGraph state inputs.

LangGraph's ``add_messages`` reducer replaces a message with the same ID, so a
checkpointed thread keeps one copy of the instructions across turns.
"""

_UNSUPPORTED_INPUT = (
    "Cannot add xstructured instructions to input of type {type_name}. Pass a string, a "
    "PromptValue, a sequence of messages, or a state mapping with a {key!r} key; pass a "
    "custom InstructionInjector; or create the wrapper with inject_instructions=False "
    "and include its `instructions` in your prompt."
)


class MessageInstructionInjector(InstructionInjector):
    """Add instructions to strings, prompt values, messages, and LangGraph state.

    Strings get the instructions appended. Prompt values and message sequences
    get them as a system message: appended to a leading system message when
    there is one, otherwise prepended as a new one. A mapping with a
    *messages_key* key, such as the input of a LangGraph graph or a LangChain
    agent, gets the same treatment for its messages; a new system message there
    has the ID `INSTRUCTIONS_MESSAGE_ID`. Messages that already carry the
    instructions are left as they are, and the input is never modified.

    Args:
        messages_key: The state key holding the messages.
    """

    def __init__(self, *, messages_key: str = "messages") -> None:
        self.messages_key = messages_key

    def __repr__(self) -> str:
        return f"MessageInstructionInjector(messages_key={self.messages_key!r})"

    @override
    def inject(self, value: Any, instructions: str) -> Any:
        if isinstance(value, str):
            return f"{value}\n\n{instructions}"
        if isinstance(value, PromptValue):
            return ChatPromptValue(
                messages=with_system_instructions(
                    value.to_messages(), instructions
                )
            )
        if isinstance(value, Mapping):
            if self.messages_key not in value:
                raise self._unsupported(value)
            messages = self._messages(value, value[self.messages_key])
            return {
                **value,
                self.messages_key: with_system_instructions(
                    messages, instructions, message_id=INSTRUCTIONS_MESSAGE_ID
                ),
            }
        return with_system_instructions(
            self._messages(value, value), instructions
        )

    def _messages(self, value: Any, messages: Any) -> list[BaseMessage]:
        if not isinstance(messages, Sequence) or isinstance(
            messages, (str, bytes, bytearray)
        ):
            raise self._unsupported(value)
        try:
            return convert_to_messages(messages)
        except (KeyError, NotImplementedError, TypeError, ValueError) as exc:
            raise self._unsupported(value) from exc

    def _unsupported(self, value: Any) -> TypeError:
        return TypeError(
            _UNSUPPORTED_INPUT.format(
                type_name=type(value).__name__, key=self.messages_key
            )
        )


class MessageTextExtractor(OutputTextExtractor):
    """Read response text from strings, messages, and LangGraph outputs.

    A complete output may be a string, a message, or a state mapping, whose last
    AI message is the response. A streamed chunk may also be a LangGraph
    ``messages``-mode ``(message, metadata)`` tuple: AI message chunks yield
    their text, and every other message yields ``""``.

    Args:
        messages_key: The state key holding the messages.
        nodes: When set, only stream chunks from these LangGraph nodes count.
    """

    def __init__(
        self,
        *,
        messages_key: str = "messages",
        nodes: Iterable[str] | None = None,
    ) -> None:
        self.messages_key = messages_key
        self.nodes = None if nodes is None else frozenset(nodes)

    def __repr__(self) -> str:
        nodes = None if self.nodes is None else sorted(self.nodes)
        return f"MessageTextExtractor(messages_key={self.messages_key!r}, nodes={nodes!r})"

    @override
    def text(self, output: Any) -> str:
        if isinstance(output, str):
            return output
        if isinstance(output, BaseMessage):
            return output.text
        if isinstance(output, Mapping) and isinstance(
            messages := output.get(self.messages_key), Sequence
        ):
            for message in reversed(messages):
                if isinstance(message, AIMessage):
                    return message.text
            raise TypeError(
                f"The output's {self.messages_key!r} contain no AI message"
            )
        raise TypeError(
            "The wrapped Runnable must return str, BaseMessage, or a state mapping "
            f"with a {self.messages_key!r} key, not {type(output).__name__}"
        )

    @override
    def chunk_text(self, chunk: Any) -> str:
        message = self.stream_message(chunk)
        if message is not None:
            return message.text
        if _is_message_tuple(chunk):
            return ""
        return self.text(chunk)

    def stream_message(self, chunk: Any) -> BaseMessage | None:
        """Return the AI message of a ``messages``-mode chunk that passes the filter."""
        if not _is_message_tuple(chunk):
            return None
        message, metadata = chunk
        if not isinstance(message, AIMessage):
            return None
        if self.nodes is not None and (
            not isinstance(metadata, Mapping)
            or metadata.get("langgraph_node") not in self.nodes
        ):
            return None
        return message


class ChunkAccumulator:
    """Collect streamed output chunks and their text."""

    def __init__(self, extractor: OutputTextExtractor) -> None:
        self._extractor = extractor
        self._chunks: list[Any] = []
        self._parts: list[str] = []

    @property
    def text(self) -> str:
        """The concatenated text of all chunks."""
        return "".join(self._parts)

    def add(self, chunk: Any) -> str:
        """Record *chunk* and return its text."""
        text = self._extractor.chunk_text(chunk)
        if _is_message_tuple(chunk):
            if not text:
                return text
            chunk = chunk[0]
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


def _is_message_tuple(chunk: Any) -> bool:
    return (
        isinstance(chunk, tuple)
        and len(chunk) == _MESSAGE_TUPLE_LENGTH
        and isinstance(chunk[0], BaseMessage)
    )


def with_system_instructions(
    messages: list[BaseMessage],
    instructions: str,
    *,
    message_id: str | None = None,
) -> list[BaseMessage]:
    if messages and isinstance(messages[0], SystemMessage):
        first = messages[0]
        content = first.content
        if instructions in (
            content if isinstance(content, str) else first.text
        ):
            return messages
        merged: str | list[str | dict[str, Any]] = (
            (f"{content}\n\n{instructions}" if content else instructions)
            if isinstance(content, str)
            else [*content, {"type": "text", "text": instructions}]
        )
        return [first.model_copy(update={"content": merged}), *messages[1:]]
    return [SystemMessage(content=instructions, id=message_id), *messages]
