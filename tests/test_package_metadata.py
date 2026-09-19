"""Sanity checks that xstructured's package metadata is coherent.

These are intentionally independent of the parsing/streaming/LangChain
implementation (covered by tests/unit and tests/integration): they only
verify the packaging and public-API surface that this repository's tooling
is responsible for.
"""

from __future__ import annotations

import importlib.metadata
import pathlib
import tomllib

import xstructured

_PYPROJECT = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"


def test_installed_distribution_version_matches_pyproject() -> None:
    declared = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
    assert importlib.metadata.version("xstructured") == declared


def test_public_api_symbols_are_exported() -> None:
    expected = {
        "EnvelopeScanner",
        "EnvelopeSpec",
        "ParseResult",
        "ParserConfig",
        "RecoveryConfig",
        "SchemaInfo",
        "StreamDecoder",
        "StreamEvent",
        "StreamEventKind",
        "StructuredParser",
        "XStructuredResult",
        "XStructuredRunnable",
        "fingerprint_schema",
        "inspect_schema",
        "schema_instructions",
        "with_xstructured_output",
    }
    assert expected.issubset(set(xstructured.__all__))
    for name in expected:
        assert hasattr(xstructured, name), f"xstructured.{name} is declared but not importable"


def test_package_is_typed() -> None:
    package_dir = pathlib.Path(xstructured.__file__).parent
    assert (package_dir / "py.typed").is_file()
