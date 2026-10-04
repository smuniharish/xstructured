"""Reproducible, offline comparison of structured-output parsers."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from pydantic import BaseModel, ConfigDict, ValidationError

from xstructured import EnvelopeSpec, ParseError, StructuredParser

CASES_PATH = Path(__file__).with_name("cases.json")
_MARKS = {True: ":white_check_mark:", False: ":x:"}


class BenchmarkPayload(BaseModel):
    """Schema shared by every parser mechanism."""

    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    score: int


@dataclass(frozen=True, slots=True)
class Case:
    """One fixture: model output and the value a correct parser returns, if any."""

    name: str
    text: str
    expected: BenchmarkPayload | None


@dataclass(frozen=True, slots=True)
class Mechanism:
    """A parser under test and the exceptions it uses to reject input."""

    name: str
    label: str
    parse: Callable[[str], BenchmarkPayload]
    rejections: tuple[type[Exception], ...]


@dataclass(frozen=True, slots=True)
class CaseResult:
    """Whether each mechanism handled one fixture correctly."""

    name: str
    must_reject: bool
    correct: tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class Row:
    """Aggregated results of one mechanism."""

    mechanism: str
    label: str
    cases: int
    operations: int
    correct: int
    correct_percent: float
    median_us: float
    mean_us: float


def mechanisms() -> tuple[Mechanism, ...]:
    """Return the compared mechanisms, in report order."""
    json_parser = JsonOutputParser()
    pydantic_parser = PydanticOutputParser(pydantic_object=BenchmarkPayload)
    xstructured_parser = StructuredParser(
        BenchmarkPayload, envelope=EnvelopeSpec()
    )

    def plain(text: str) -> BenchmarkPayload:
        return BenchmarkPayload.model_validate(json.loads(text))

    def langchain_json(text: str) -> BenchmarkPayload:
        return BenchmarkPayload.model_validate(json_parser.parse(text))

    def xstructured(text: str) -> BenchmarkPayload:
        return xstructured_parser.parse(text).value

    return (
        Mechanism(
            "plain-json+pydantic",
            "Plain JSON",
            plain,
            (json.JSONDecodeError, ValidationError),
        ),
        Mechanism(
            "langchain-json-parser",
            "LangChain JSON",
            langchain_json,
            (OutputParserException, ValidationError),
        ),
        Mechanism(
            "langchain-pydantic-parser",
            "LangChain Pydantic",
            pydantic_parser.parse,
            (OutputParserException,),
        ),
        Mechanism("xstructured", "xstructured", xstructured, (ParseError,)),
    )


def load_cases(selected: set[str] | None = None) -> tuple[Case, ...]:
    """Load fixtures, optionally only the named ones.

    Raises:
        ValueError: If a selected name does not exist.
    """
    raw_cases: list[dict[str, Any]] = json.loads(
        CASES_PATH.read_text(encoding="utf-8")
    )
    cases = tuple(
        Case(
            name=item["name"],
            text=item["text"],
            expected=None
            if item["expected"] is None
            else BenchmarkPayload.model_validate(item["expected"]),
        )
        for item in raw_cases
        if selected is None or item["name"] in selected
    )
    missing = (selected or set()).difference(case.name for case in cases)
    if missing:
        raise ValueError(f"Unknown case(s): {', '.join(sorted(missing))}")
    return cases


def is_correct(mechanism: Mechanism, case: Case) -> bool:
    """Whether *mechanism* returns the expected value, or rejects an invalid case."""
    try:
        value = mechanism.parse(case.text)
    except mechanism.rejections:
        return case.expected is None
    return value == case.expected


def run(
    selected: Sequence[Mechanism],
    cases: Sequence[Case],
    *,
    iterations: int,
    warmup: int,
) -> list[Row]:
    """Measure correctness and per-operation latency of every mechanism."""
    rows: list[Row] = []
    for mechanism in selected:
        for _ in range(warmup):
            for case in cases:
                is_correct(mechanism, case)
        samples: list[int] = []
        correct = 0
        for _ in range(iterations):
            for case in cases:
                started = time.perf_counter_ns()
                correct += is_correct(mechanism, case)
                samples.append(time.perf_counter_ns() - started)
        rows.append(
            Row(
                mechanism=mechanism.name,
                label=mechanism.label,
                cases=len(cases),
                operations=len(samples),
                correct=correct,
                correct_percent=round(correct * 100 / len(samples), 2),
                median_us=round(statistics.median(samples) / 1_000, 2),
                mean_us=round(statistics.fmean(samples) / 1_000, 2),
            )
        )
    return rows


def render_table(rows: Sequence[Row]) -> str:
    """Render rows as an aligned plain-text table."""
    headers = ("mechanism", "correct", "correct %", "median us", "mean us")
    body = [
        (
            row.mechanism,
            f"{row.correct}/{row.operations}",
            f"{row.correct_percent:.2f}",
            f"{row.median_us:.2f}",
            f"{row.mean_us:.2f}",
        )
        for row in rows
    ]
    widths = [
        max(len(line[index]) for line in (headers, *body)) for index in range(5)
    ]
    lines: list[str] = [
        "  ".join(
            cell.ljust(width) for cell, width in zip(line, widths, strict=True)
        )
        for line in (headers, *body)
    ]
    lines.insert(1, "  ".join("-" * width for width in widths))
    return "\n".join(lines) + "\n"


def render_markdown(
    rows: Sequence[Row],
    *,
    iterations: int,
    matrix: Sequence[CaseResult] = (),
) -> str:
    """Render rows, an optional per-case matrix, and the environment as Markdown.

    The output is ASCII: emoji are shortcodes, which MkDocs and GitHub render.
    """
    lines = [
        "| Mechanism | Correct | Correct % | Median (&micro;s) | Mean (&micro;s) |",
        "| --- | ---: | ---: | ---: | ---: |",
        *(
            f"| {row.label} | {row.correct}/{row.operations} | "
            f"{row.correct_percent:.2f} | {row.median_us:.2f} | "
            f"{row.mean_us:.2f} |"
            for row in rows
        ),
    ]
    header = "| Case | " + " | ".join(row.label for row in rows) + " |"
    separator = "| --- |" + " :---: |" * len(rows)
    for title, must_reject in (
        ("Inputs that must parse:", False),
        ("Inputs that must be rejected:", True),
    ):
        results = [
            result for result in matrix if result.must_reject is must_reject
        ]
        if results:
            lines += ["", title, "", header, separator]
            lines += [
                f"| `{result.name}` | "
                + " | ".join(_MARKS[ok] for ok in result.correct)
                + " |"
                for result in results
            ]
    environment = (
        f"Measured with {iterations} iterations per case on Python "
        f"{platform.python_version()} "
        f"({platform.system()} {platform.machine()}), "
        f"xstructured {version('xstructured')}, "
        f"langchain-core {version('langchain-core')}, "
        f"pydantic {version('pydantic')}."
    )
    lines += ["", environment]
    return "\n".join(lines) + "\n"


def correctness_matrix(
    selected: Sequence[Mechanism], cases: Sequence[Case]
) -> list[CaseResult]:
    """Return, for every case, whether each mechanism handles it correctly."""
    return [
        CaseResult(
            name=case.name,
            must_reject=case.expected is None,
            correct=tuple(
                is_correct(mechanism, case) for mechanism in selected
            ),
        )
        for case in cases
    ]


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="python -m benchmarks",
        description=(
            "Compare plain JSON, LangChain output parsers, and xstructured "
            "against local fixtures. No network calls are made."
        ),
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1_000,
        help="measured repetitions (default: 1000)",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=100,
        help="unmeasured warmup repetitions (default: 100)",
    )
    parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        metavar="NAME",
        help="run one fixture by name; repeat to select several",
    )
    parser.add_argument(
        "--list-cases", action="store_true", help="list fixture names and exit"
    )
    parser.add_argument(
        "--format",
        choices=("table", "json", "markdown"),
        default="table",
        help="output format (default: table)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the benchmark command line and return the exit status."""
    args = build_parser().parse_args(argv)
    if args.iterations < 1:
        raise SystemExit("--iterations must be at least 1")
    if args.warmup < 0:
        raise SystemExit("--warmup cannot be negative")
    cases = load_cases(set(args.cases) if args.cases else None)
    if args.list_cases:
        sys.stdout.write("".join(f"{case.name}\n" for case in cases))
        return 0
    rows = run(
        mechanisms(), cases, iterations=args.iterations, warmup=args.warmup
    )
    if args.format == "json":
        sys.stdout.write(
            json.dumps([asdict(row) for row in rows], indent=2) + "\n"
        )
    elif args.format == "markdown":
        matrix = correctness_matrix(mechanisms(), cases)
        sys.stdout.write(
            render_markdown(rows, iterations=args.iterations, matrix=matrix)
        )
    else:
        sys.stdout.write(render_table(rows))
    return 0
