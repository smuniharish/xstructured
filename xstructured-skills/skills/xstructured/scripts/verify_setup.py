"""Check that xstructured is installed and works in this Python environment.

Runs offline and changes nothing. Prints one PASS, FAIL, or INFO line per check:

    python scripts/verify_setup.py           # core; agents too when installed
    python scripts/verify_setup.py --agents  # require the agents extra
    python scripts/verify_setup.py --json    # one JSON object on stdout

Exit codes: 0 every check passed, 1 a check failed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import re
import sys
from importlib import metadata

REQUIRED = {
    "langchain-core": ((1, 7, 6), (2,)),
    "pydantic": ((2, 14, 3), (3,)),
}
AGENTS = {
    "langchain": ((1, 4, 9), (2,)),
}
OPTIONAL = ("langgraph", "deepagents", "opentelemetry-api", "langsmith")
REPLY = (
    "The deploy is healthy. "
    '<xstructured>{"status": "healthy", "next_step": "Promote."}</xstructured>'
)

failures: list[str] = []
results: list[dict[str, str]] = []
as_json = False


def emit(status: str, message: str) -> None:
    results.append({"status": status, "message": message})
    if not as_json:
        print(f"{status}  {message}")


def report(passed: bool, message: str) -> bool:  # noqa: FBT001
    emit("PASS" if passed else "FAIL", message)
    if not passed:
        failures.append(message)
    return passed


def installed(distribution: str) -> str | None:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


def release(version: str) -> tuple[int, ...]:
    """The numeric release of a version string: "1.2.12rc1" -> (1, 2, 12)."""
    numbers = []
    for part in version.split(".")[:3]:
        digits = re.match(r"\d+", part)
        numbers.append(int(digits.group()) if digits else 0)
    return tuple(numbers)


def dotted(version: tuple[int, ...]) -> str:
    return ".".join(map(str, version))


def check_environment(*, agents: bool) -> bool:
    report(
        sys.version_info >= (3, 12),
        f"Python {platform.python_version()} (3.12 or newer required)",
    )
    version = installed("xstructured")
    if version is None:
        return report(
            False, "xstructured is not installed: pip install xstructured"
        )
    report(
        release(version)[:1] == (1,),
        f"xstructured {version} (1.x expected by this skill)",
    )
    required = REQUIRED | AGENTS if agents else REQUIRED
    for distribution, (lowest, below) in required.items():
        found = installed(distribution)
        compatible = found is not None and lowest <= release(found) < below
        report(
            compatible,
            f"{distribution} {found or 'is not installed'} "
            f"(>={dotted(lowest)},<{dotted(below)} required)"
            + (
                '; install "xstructured[agents]"'
                if distribution in AGENTS and not compatible
                else ""
            ),
        )
    extras = {name: installed(name) for name in OPTIONAL}
    present = [f"{name} {found}" for name, found in extras.items() if found]
    absent = [name for name, found in extras.items() if not found]
    emit(
        "INFO",
        f"optional integrations: {', '.join(present) or 'none'}"
        + (f" (not installed: {', '.join(absent)})" if absent else ""),
    )
    return not failures


def status_schema() -> type:
    from pydantic import BaseModel

    class Status(BaseModel):
        status: str
        next_step: str

    return Status


async def check_parser() -> None:
    from xstructured import EnvelopeSpec, ParseError, StructuredParser

    parser = StructuredParser(status_schema(), envelope=EnvelopeSpec())
    result = parser.parse(REPLY)
    fenced = StructuredParser(status_schema()).parse(
        '```json\n{"status": "ok", "next_step": "none"}\n```'
    )
    try:
        parser.parse("No envelope at all.")
    except ParseError:
        rejected = True
    else:
        rejected = False
    report(
        result.value.status == "healthy" and fenced.recovered and rejected,
        "parser extracts envelopes, recovers fenced JSON, and rejects bad output",
    )


async def check_wrapper() -> None:
    from xstructured import StreamEventKind, with_xstructured_output
    from xstructured.testing import ScriptedChatModel

    schema = status_schema()
    result = await with_xstructured_output(
        ScriptedChatModel.of(REPLY), schema
    ).ainvoke("How did the deploy go?")
    report(
        result.structured.status == "healthy"
        and result.content == "The deploy is healthy. ",
        "with_xstructured_output returns prose and a validated value",
    )
    kinds = [
        event.kind
        async for event in with_xstructured_output(
            ScriptedChatModel.of(REPLY), schema
        ).astream("How did the deploy go?")
    ]
    report(
        kinds[0] is StreamEventKind.TEXT_DELTA
        and StreamEventKind.STRUCTURED_END in kinds
        and kinds[-1] is StreamEventKind.RESULT,
        f"astream yields protocol events ({len(kinds)} events)",
    )


async def check_agent() -> None:
    from langchain.agents import create_agent

    from xstructured.agents import XStructuredMiddleware
    from xstructured.testing import ScriptedChatModel

    agent = create_agent(
        ScriptedChatModel.of(REPLY),
        middleware=[XStructuredMiddleware(status_schema())],
    )
    state = await agent.ainvoke({"messages": [("human", "How did it go?")]})
    result = state["structured_response"]
    report(
        result.structured.next_step == "Promote."
        and "<xstructured>" in state["messages"][-1].text,
        "XStructuredMiddleware puts the validated answer in agent state",
    )


def main() -> int:
    global as_json  # noqa: PLW0603
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--agents", action="store_true", help="Require the agents extra."
    )
    parser.add_argument(
        "--json", action="store_true", help="Print one JSON object to stdout."
    )
    arguments = parser.parse_args()
    as_json = arguments.json
    agents = arguments.agents or installed("langchain") is not None
    if not agents:
        emit(
            "INFO",
            'Agent checks skipped; install "xstructured[agents]" to enable them.',
        )
    if check_environment(agents=agents):
        checks = [check_parser, check_wrapper]
        if agents:
            checks.append(check_agent)
        for check in checks:
            try:
                asyncio.run(check())
            except (
                Exception
            ) as error:  # report every failing check, then the summary
                report(
                    False, f"{check.__name__}: {type(error).__name__}: {error}"
                )
    summary = (
        "All checks passed."
        if not failures
        else f"{len(failures)} check(s) failed."
    )
    if as_json:
        print(
            json.dumps(
                {"ok": not failures, "summary": summary, "checks": results},
                indent=2,
            )
        )
    else:
        print(summary)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
