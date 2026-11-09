"""Helpers shared by the example scripts.

Every example runs in one of two modes:

- **Live**, when ``EXPLABS_API_KEY`` is set: requests go to the Experiential
  Labs OpenAI-compatible API. ``EXPLABS_MODEL`` and ``EXPLABS_BASE_URL``
  override the model and endpoint.
- **Offline**, otherwise: a scripted chat model replays realistic responses,
  so every example runs anywhere without credentials or network access.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from xstructured.testing import ScriptedChatModel

DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_BASE_URL = "https://api.experientiallabs.ai/v1"


def is_live() -> bool:
    """Whether the examples call the live Experiential Labs API."""
    return bool(os.environ.get("EXPLABS_API_KEY"))


@asynccontextmanager
async def chat_model(
    *scripted: str | AIMessage,
) -> AsyncGenerator[BaseChatModel]:
    """Yield the live chat model, or an offline one replaying *scripted*.

    The live model's HTTP connections are closed on exit.
    """
    if not is_live():
        yield ScriptedChatModel.of(*scripted)
        return
    import openai
    from langchain_openai import ChatOpenAI

    async with openai.DefaultAsyncHttpxClient() as http_client:
        yield ChatOpenAI(
            model=os.environ.get("EXPLABS_MODEL", DEFAULT_MODEL),
            base_url=os.environ.get("EXPLABS_BASE_URL", DEFAULT_BASE_URL),
            api_key=os.environ["EXPLABS_API_KEY"],
            http_async_client=http_client,
        )


def banner(title: str) -> None:
    """Print the example title and the mode it runs in."""
    mode = (
        f"live: {os.environ.get('EXPLABS_MODEL', DEFAULT_MODEL)}"
        if is_live()
        else "offline: scripted model"
    )
    print(f"=== {title} ({mode}) ===")
