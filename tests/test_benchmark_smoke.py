from __future__ import annotations

import json

from benchmarks.runner import main


def test_benchmark_help_is_runnable(capsys) -> None:
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    assert "No network calls are made" in capsys.readouterr().out


def test_benchmark_runs_all_mechanisms_offline(capsys) -> None:
    assert main(["--iterations", "1", "--warmup", "0", "--format", "json"]) == 0

    rows = json.loads(capsys.readouterr().out)
    assert [row["mechanism"] for row in rows] == [
        "plain-json+pydantic",
        "langchain-json-parser",
        "langchain-pydantic-parser",
        "xstructured",
    ]
    assert all(row["operations"] == 8 for row in rows)
