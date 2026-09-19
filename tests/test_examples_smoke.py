"""Smoke-tests for the example scripts in examples/.

The example scripts are meant to run in credential-free environments (like
CI) by printing an explanation and exiting with status 0 when a required
environment variable or optional package is missing. This test runs each
script exactly that way -- with no provider credentials -- and asserts
that it exits cleanly, without ever making a network call.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

_EXAMPLES_DIR = pathlib.Path(__file__).resolve().parent.parent / "examples"
_SCRIPTS = sorted(path for path in _EXAMPLES_DIR.glob("*.py") if not path.name.startswith("_"))
_PRODUCTION_EXAMPLES = {
    "langgraph_workflow.py",
    "rag_citations.py",
    "incident_analysis.py",
    "streaming_ui_events.py",
}


def test_production_examples_are_part_of_smoke_suite() -> None:
    assert {path.name for path in _SCRIPTS} >= _PRODUCTION_EXAMPLES


@pytest.mark.parametrize("script", _SCRIPTS, ids=lambda path: path.name)
def test_example_script_runs_cleanly_without_credentials(
    script: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("EXPLABS_API_KEY", raising=False)
    monkeypatch.delenv("EXPLABS_BASE_URL", raising=False)
    monkeypatch.delenv("EXPLABS_MODEL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=_EXAMPLES_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, (
        f"{script.name} exited {completed.returncode} without credentials:\n"
        f"{completed.stdout}\n{completed.stderr}"
    )
    assert "Skipping example" in completed.stdout
