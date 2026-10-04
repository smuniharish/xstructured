"""Helpers shared by the example scripts.

Every example runs in one of two modes:

- **Live**, when ``EXPLABS_API_KEY`` is set: requests go to the Experiential
  Labs OpenAI-compatible API. ``EXPLABS_MODEL`` and ``EXPLABS_BASE_URL``
  override the model and endpoint.
- **Offline**, otherwise: a scripted chat model replays realistic responses,
  so every example runs anywhere without credentials or network access.
"""

from __future__ import annotations

import importlib.util
import os
from collections.abc import Sequence
from typing import Any, override

from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_BASE_URL = "https://api.experientiallabs.ai/v1"


class ScriptedChatModel(GenericFakeChatModel):
    """Offline chat model that replays scripted responses and accepts tools."""

    @override
    def bind_tools(
        self, tools: Sequence[Any], **kwargs: Any
    ) -> ScriptedChatModel:
        """Accept tool definitions; scripted responses never call tools."""
        return self


def is_live() -> bool:
    """Whether the examples call the live Experiential Labs API."""
    return bool(os.environ.get("EXPLABS_API_KEY"))


def chat_model(*scripted: str) -> BaseChatModel:
    """Return the live chat model, or an offline one replaying *scripted*."""
    if is_live():
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.environ.get("EXPLABS_MODEL", DEFAULT_MODEL),
            base_url=os.environ.get("EXPLABS_BASE_URL", DEFAULT_BASE_URL),
            api_key=os.environ["EXPLABS_API_KEY"],
        )
    return ScriptedChatModel(
        messages=iter([AIMessage(content=text) for text in scripted])
    )


def require_packages(*modules: str) -> None:
    """Exit with setup guidance when an optional dependency is missing."""
    missing = [
        module for module in modules if importlib.util.find_spec(module) is None
    ]
    if missing:
        print(
            f"This example needs {', '.join(missing)}. Install the example "
            "dependencies with:\n  uv sync --group examples"
        )
        raise SystemExit(0)


def banner(title: str) -> None:
    """Print the example title and the mode it runs in."""
    mode = (
        f"live: {os.environ.get('EXPLABS_MODEL', DEFAULT_MODEL)}"
        if is_live()
        else "offline: scripted model"
    )
    print(f"=== {title} ({mode}) ===")
