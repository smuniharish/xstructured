"""The example scripts run offline with asserted output, and live on request (``-m live``)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
EXPECTED = {
    "single_agent_extraction.py": "ContactInfo(name='Priya Shah', email='priya.shah@example.com'",
    "multi_agent_pipeline.py": "ClaimReview(approved=True",
    "deep_agent.py": "Topic: Retrieval-augmented generation",
    "langgraph_workflow.py": "Action: Paged the payments on-call engineer",
    "rag_citations.py": "(verified: True)",
    "incident_analysis.py": "Severity:       high",
    "streaming_ui_events.py": "[card ready after",
    "multiple_payloads_repair.py": "Repaired: True (attempts: 1)",
    "named_envelopes.py": "recommendation: Recommendation(owner='platform'",
}


def run_example(name: str, *, live: bool) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("EXPLABS_")
    }
    if live:
        env.update(
            {
                key: value
                for key, value in os.environ.items()
                if key.startswith("EXPLABS_")
            }
        )
    return subprocess.run(  # noqa: S603 - runs a repository script with the test interpreter
        [sys.executable, str(EXAMPLES / name)],
        cwd=EXAMPLES,
        env=env | {"PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
        check=False,
    )


def test_every_example_is_covered() -> None:
    scripts = {
        path.name
        for path in EXAMPLES.glob("*.py")
        if not path.name.startswith("_")
    }

    assert scripts == set(EXPECTED)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_examples_run_offline(name: str) -> None:
    completed = run_example(name, live=False)

    assert completed.returncode == 0, completed.stderr
    assert "(offline: scripted model)" in completed.stdout
    assert EXPECTED[name] in completed.stdout


@pytest.mark.live
@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_examples_run_live(name: str) -> None:
    if not os.environ.get("EXPLABS_API_KEY"):
        pytest.skip("EXPLABS_API_KEY is not set")

    completed = run_example(name, live=True)

    assert completed.returncode == 0, completed.stderr
    assert "(live: " in completed.stdout
