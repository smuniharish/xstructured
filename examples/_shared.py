"""Shared helpers for the runnable example scripts in this directory."""

from __future__ import annotations

import os


def require_env(*names: str, install_hint: str | None = None) -> None:
    """Exit cleanly with guidance when required environment variables are missing.

    This keeps example scripts runnable in CI and other credential-free
    environments: missing configuration is treated as "skip", not "fail".
    """
    missing = [name for name in names if not os.environ.get(name)]
    if not missing:
        return
    print(
        "Skipping example: missing required environment variable(s) "
        f"{', '.join(missing)}.\n"
        "Set them to your provider credentials to run this example live, e.g.\n"
        f'  $env:{missing[0]} = "..."   # PowerShell\n'
        f"  export {missing[0]}=...       # bash/zsh"
    )
    if install_hint:
        print(install_hint)
    raise SystemExit(0)


def require_package(module_name: str, *, extra_group: str) -> None:
    """Exit cleanly with guidance when an optional example dependency is absent."""
    import importlib.util

    if importlib.util.find_spec(module_name) is not None:
        return
    print(
        f"Skipping example: the '{module_name}' package is not installed.\n"
        f"Install it with:\n"
        f"  uv sync --group {extra_group}"
    )
    raise SystemExit(0)


def explabs_chat_model():
    """Create the OpenAI-compatible model used by live examples.

    Provider configuration intentionally lives in examples, not in the
    xstructured runtime package.
    """
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=os.environ.get("EXPLABS_MODEL", "gpt-5.6-luna"),
        api_key=os.environ["EXPLABS_API_KEY"],
        base_url=os.environ.get(
            "EXPLABS_BASE_URL",
            "https://api.experientiallabs.ai/v1",
        ),
    )


def print_result_header(title: str) -> None:
    print(f"\n=== {title} ===")


def print_structured(label: str, value: object) -> None:
    print(f"{label}: {value!r}")
