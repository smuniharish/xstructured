"""Test doubles and models shared by the test suite."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any, override

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from pydantic import BaseModel


class Answer(BaseModel):
    value: int


class Label(BaseModel):
    name: str


class Note(BaseModel):
    text: str


def reply(text: Any) -> RunnableLambda[Any, Any]:
    """A Runnable that ignores its input and returns *text*."""
    return RunnableLambda(lambda _: text)


class Recorder:
    """A Runnable body that records its inputs and returns scripted outputs in order."""

    def __init__(self, *outputs: Any) -> None:
        self.inputs: list[Any] = []
        self._outputs = list(outputs)

    def __call__(self, value: Any) -> Any:
        self.inputs.append(value)
        return self._outputs[min(len(self.inputs), len(self._outputs)) - 1]

    async def acall(self, value: Any) -> Any:
        return self(value)


class ChunkRunnable(Runnable[Any, Any]):
    """A Runnable that streams fixed chunks and records its inputs."""

    def __init__(self, chunks: Sequence[Any]) -> None:
        self.chunks = list(chunks)
        self.inputs: list[Any] = []

    @override
    def invoke(
        self, input: Any, config: RunnableConfig | None = None, **kwargs: Any
    ) -> Any:
        self.inputs.append(input)
        if all(isinstance(chunk, str) for chunk in self.chunks):
            return "".join(self.chunks)
        merged = self.chunks[0]
        for chunk in self.chunks[1:]:
            merged += chunk
        return merged

    def stream(
        self,
        input: Any,  # noqa: A002
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Iterator[Any]:
        self.inputs.append(input)
        yield from self.chunks

    async def astream(
        self,
        input: Any,  # noqa: A002
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        self.inputs.append(input)
        for chunk in self.chunks:
            yield chunk


class RunLog(BaseCallbackHandler):
    """Records chain runs: name, run id, parent run id, and tags."""

    def __init__(self) -> None:
        self.starts: list[dict[str, Any]] = []
        self.ends: list[Any] = []

    def on_chain_start(
        self,
        serialized: dict[str, Any] | None,
        inputs: Any,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        self.starts.append(
            {
                "name": kwargs.get("name"),
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "tags": tags or [],
            }
        )

    def on_chain_end(self, outputs: Any, **kwargs: Any) -> None:
        self.ends.append(outputs)

    def by_name(self, name: str) -> dict[str, Any]:
        return next(start for start in self.starts if start["name"] == name)


def chunked(text: str, widths: Sequence[int]) -> list[str]:
    """Split *text* into chunks of the given widths, then the remainder."""
    chunks: list[str] = []
    offset = 0
    for width in widths:
        if offset >= len(text):
            break
        chunks.append(text[offset : offset + width])
        offset += width
    if offset < len(text):
        chunks.append(text[offset:])
    return chunks
