"""Reproducible, offline parser comparison."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from pydantic import BaseModel, ConfigDict, ValidationError

from xstructured import EnvelopeSpec, StructuredParser
from xstructured.core import ParseError

_CASES_PATH = Path(__file__).with_name("cases.json")


class BenchmarkPayload(BaseModel):
    """Schema shared by every parser mechanism."""

    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    score: int


@dataclass(frozen=True, slots=True)
class Case:
    name: str
    text: str
    expected: BenchmarkPayload | None


@dataclass(frozen=True, slots=True)
class Mechanism:
    name: str
    parse: Callable[[str], BenchmarkPayload]
    expected_errors: tuple[type[Exception], ...]


def _plain_parse(text: str) -> BenchmarkPayload:
    return BenchmarkPayload.model_validate(json.loads(text))


def _mechanisms() -> tuple[Mechanism, ...]:
    json_parser = JsonOutputParser()
    pydantic_parser = PydanticOutputParser(pydantic_object=BenchmarkPayload)
    xstructured_parser: StructuredParser[BenchmarkPayload] = StructuredParser(
        BenchmarkPayload, envelope=EnvelopeSpec()
    )

    def langchain_json(text: str) -> BenchmarkPayload:
        return BenchmarkPayload.model_validate(json_parser.parse(text))

    def langchain_pydantic(text: str) -> BenchmarkPayload:
        return pydantic_parser.parse(text)

    def xstructured(text: str) -> BenchmarkPayload:
        return xstructured_parser.parse(text).value

    return (
        Mechanism("plain-json+pydantic", _plain_parse, (json.JSONDecodeError, ValidationError)),
        Mechanism(
            "langchain-json-parser",
            langchain_json,
            (OutputParserException, ValidationError),
        ),
        Mechanism(
            "langchain-pydantic-parser",
            langchain_pydantic,
            (OutputParserException,),
        ),
        Mechanism("xstructured", xstructured, (ParseError,)),
    )


def _load_cases(selected: set[str] | None = None) -> tuple[Case, ...]:
    raw_cases: list[dict[str, Any]] = json.loads(_CASES_PATH.read_text(encoding="utf-8"))
    cases = tuple(
        Case(
            name=item["name"],
            text=item["text"],
            expected=(
                BenchmarkPayload.model_validate(item["expected"])
                if item["expected"] is not None
                else None
            ),
        )
        for item in raw_cases
        if selected is None or item["name"] in selected
    )
    if selected:
        missing = selected.difference(case.name for case in cases)
        if missing:
            raise ValueError(f"Unknown case(s): {', '.join(sorted(missing))}")
    return cases


def _is_correct(mechanism: Mechanism, case: Case) -> bool:
    try:
        value = mechanism.parse(case.text)
    except mechanism.expected_errors:
        return case.expected is None
    return case.expected is not None and value == case.expected


def _benchmark(
    mechanisms: Sequence[Mechanism],
    cases: Sequence[Case],
    *,
    iterations: int,
    warmup: int,
) -> list[dict[str, int | float | str]]:
    rows: list[dict[str, int | float | str]] = []
    for mechanism in mechanisms:
        for _ in range(warmup):
            for case in cases:
                _is_correct(mechanism, case)

        samples: list[int] = []
        correct = 0
        for _ in range(iterations):
            for case in cases:
                started = time.perf_counter_ns()
                correct += _is_correct(mechanism, case)
                samples.append(time.perf_counter_ns() - started)

        total = len(samples)
        rows.append(
            {
                "mechanism": mechanism.name,
                "cases": len(cases),
                "operations": total,
                "correct": correct,
                "correct_percent": round(correct * 100 / total, 2),
                "median_us": round(statistics.median(samples) / 1_000, 2),
                "mean_us": round(statistics.fmean(samples) / 1_000, 2),
            }
        )
    return rows


def _print_table(rows: Sequence[dict[str, int | float | str]]) -> None:
    headers = ("mechanism", "correct", "correct %", "median us", "mean us")
    rendered = [
        (
            str(row["mechanism"]),
            f"{row['correct']}/{row['operations']}",
            f"{row['correct_percent']:.2f}",
            f"{row['median_us']:.2f}",
            f"{row['mean_us']:.2f}",
        )
        for row in rows
    ]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rendered))
        for index in range(len(headers))
    ]
    lines = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row)) for row in rendered
    )
    sys.stdout.write("\n".join(lines) + "\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare plain JSON, LangChain output parsers, and xstructured "
            "against local fixtures. No network calls are made."
        )
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1_000,
        help="measured repetitions of every selected case (default: 1000)",
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
        help="run one fixture by name; repeat to select multiple fixtures",
    )
    parser.add_argument(
        "--list-cases",
        action="store_true",
        help="list fixture names and exit",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="output format (default: table)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.iterations < 1:
        raise SystemExit("--iterations must be at least 1")
    if args.warmup < 0:
        raise SystemExit("--warmup cannot be negative")

    cases = _load_cases(set(args.cases) if args.cases else None)
    if args.list_cases:
        sys.stdout.write("".join(f"{case.name}\n" for case in cases))
        return 0

    rows = _benchmark(_mechanisms(), cases, iterations=args.iterations, warmup=args.warmup)
    if args.format == "json":
        sys.stdout.write(json.dumps(rows, indent=2) + "\n")
    else:
        _print_table(rows)
    return 0
