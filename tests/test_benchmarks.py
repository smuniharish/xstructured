from __future__ import annotations

import json

import pytest

from benchmarks.runner import CASES_PATH, load_cases, main, mechanisms


def test_help_describes_the_offline_benchmark(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])

    assert excinfo.value.code == 0
    assert "No network calls are made" in capsys.readouterr().out


def test_every_mechanism_is_measured_and_xstructured_is_always_correct(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--iterations", "1", "--warmup", "0", "--format", "json"]) == 0

    rows = {
        row["mechanism"]: row for row in json.loads(capsys.readouterr().out)
    }
    cases = len(json.loads(CASES_PATH.read_text(encoding="utf-8")))
    assert list(rows) == [mechanism.name for mechanism in mechanisms()]
    assert all(row["operations"] == cases for row in rows.values())
    assert rows["xstructured"]["correct"] == cases


@pytest.mark.parametrize("output_format", ["table", "markdown"])
def test_human_readable_formats(
    output_format: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(["--iterations", "1", "--warmup", "0", "--format", output_format])
        == 0
    )

    output = capsys.readouterr().out
    assert "xstructured" in output
    if output_format == "markdown":
        assert output.isascii()
        assert "| Case | Plain JSON | LangChain JSON |" in output
        assert "Inputs that must be rejected:" in output
        assert "| `delimiter-inside-string` | :x: |" in output
        assert "Measured with 1 iterations" in output


def test_cases_can_be_listed_and_selected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--list-cases", "--case", "valid-json"]) == 0
    assert capsys.readouterr().out == "valid-json\n"
    with pytest.raises(ValueError, match="Unknown case"):
        load_cases({"missing"})


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--iterations", "0"], "at least 1"),
        (["--warmup", "-1"], "cannot be negative"),
    ],
)
def test_invalid_arguments_are_rejected(
    arguments: list[str], message: str
) -> None:
    with pytest.raises(SystemExit, match=message):
        main(arguments)
