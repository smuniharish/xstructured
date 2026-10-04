"""Packaging and public API surface."""

from __future__ import annotations

import importlib.metadata
import inspect
import tomllib
from pathlib import Path

import xstructured

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_version_matches_the_distribution_metadata() -> None:
    assert xstructured.__version__ == importlib.metadata.version("xstructured")
    assert xstructured.__version__ == PYPROJECT["project"]["version"]


def test_the_package_is_typed() -> None:
    assert (Path(xstructured.__file__).parent / "py.typed").is_file()


def test_public_names_are_sorted_and_importable() -> None:
    names = xstructured.__all__

    assert names == sorted(names)
    assert len(set(names)) == len(names)
    for name in names:
        assert hasattr(xstructured, name), name


def test_every_public_class_and_function_is_exported() -> None:
    exported = set(xstructured.__all__)
    public = {
        name
        for name, value in vars(xstructured).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }

    assert public <= exported


def test_runtime_dependencies_are_minimal() -> None:
    requirements = importlib.metadata.requires("xstructured") or []
    runtime = sorted(
        requirement.split(">")[0].split("<")[0].strip()
        for requirement in requirements
        if "extra ==" not in requirement
    )

    assert runtime == ["langchain-core", "pydantic"]
