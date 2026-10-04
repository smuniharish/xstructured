"""Documentation code blocks are valid, use the real API, and run where marked."""

from __future__ import annotations

import ast
import inspect
import re
import sys
import textwrap
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

import xstructured

ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS = sorted(
    [
        ROOT / "README.md",
        ROOT / "CHANGELOG.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SECURITY.md",
        *ROOT.joinpath("docs").rglob("*.md"),
        *ROOT.joinpath("skills").rglob("*.md"),
        *ROOT.joinpath("examples").rglob("*.md"),
    ]
)
EXAMPLE_SCRIPTS = sorted(ROOT.joinpath("examples").glob("*.py"))
BLOCK = re.compile(
    r"^(?P<indent>[ \t]*)```python[^\n]*\n(?P<body>.*?)^(?P=indent)```",
    re.DOTALL | re.MULTILINE,
)
FENCE = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})(?P<info>[^`]*)$")
DOCSTRING_EXAMPLE = re.compile(r"```python\n(?P<body>.*?)\n\s*```", re.DOTALL)
INCLUDE = re.compile(r'^--8<-- "(?P<path>[^"]+)"$')
SNIPPET_LIKE = re.compile(r"-+\s*8\s*<\s*-+")
RUN_MARKER = "<!-- docs-test: run -->"
# The documentation column fits 80 columns of code; program output wraps instead.
CODE_WIDTH = 80
WRAPPED_LANGUAGES = frozenset({"text"})
# Diagrams are rendered at twice their display size and shown at 1x, so their text
# matches the page. The content column (with the image padding) fits 656 pixels.
DIAGRAMS = ROOT / "docs" / "assets" / "diagrams"
DIAGRAM_IMAGE = re.compile(
    r"!\[[^\]]+\]\((?:\.\./)*assets/diagrams/(?P<name>[\w-]+)\.png\)"
    r'\{ \.diagram width="(?P<width>\d+)" \}'
)
MAX_DIAGRAM_WIDTH = 656
CALLABLES: dict[str, Callable[..., Any]] = {
    name: getattr(xstructured, name)
    for name in (
        "EnvelopeScanner",
        "EnvelopeSpec",
        "NamedSchemaSpec",
        "ParserConfig",
        "RecoveryConfig",
        "RepairConfig",
        "StreamDecoder",
        "StructuredParser",
        "XStructuredRunnable",
        "canonical_schema_json",
        "fingerprint_schema",
        "inspect_named_schemas",
        "inspect_schema",
        "schema_instructions",
        "with_xstructured_output",
    )
}


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def python_blocks(path: Path) -> list[str]:
    blocks = []
    for match in BLOCK.finditer(path.read_text(encoding="utf-8")):
        indent = match.group("indent")
        lines = match.group("body").splitlines()
        block = "\n".join(line.removeprefix(indent) for line in lines)
        if include := INCLUDE.match(block.strip()):
            block = ROOT.joinpath(include.group("path")).read_text(
                encoding="utf-8"
            )
        blocks.append(block)
    return blocks


def fenced_lines(path: Path) -> Iterator[tuple[int, str, str]]:
    """Yield the line number, language, and text of each fenced code line."""
    opening: tuple[str, str] | None = None
    language = ""
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, start=1):
        fence = FENCE.match(line)
        if opening is None:
            if fence:
                opening = (fence["indent"], fence["fence"])
                language = next(iter(fence["info"].split()), "")
            continue
        indent, marker = opening
        if (
            fence
            and fence["indent"] == indent
            and fence["fence"].startswith(marker)
            and not fence["info"].strip()
        ):
            opening = None
            continue
        yield number, language, line.removeprefix(indent)


DOCUMENT_PARAMS = [pytest.param(path, id=relative(path)) for path in DOCUMENTS]


def docstring_examples() -> list[tuple[str, str]]:
    """Return the ``python`` examples in the package's docstrings, by location."""
    examples = []
    for path in sorted(ROOT.joinpath("src").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(
                node,
                ast.Module
                | ast.ClassDef
                | ast.FunctionDef
                | ast.AsyncFunctionDef,
            ):
                continue
            name = getattr(node, "name", "module")
            docstring = ast.get_docstring(node) or ""
            for index, match in enumerate(
                DOCSTRING_EXAMPLE.finditer(docstring), start=1
            ):
                where = f"{relative(path)}:{name}#{index}"
                examples.append((where, textwrap.dedent(match["body"])))
    return examples


DOCSTRING_EXAMPLES = docstring_examples()
ALL_BLOCKS = [
    *(
        pytest.param(block, id=f"{relative(path)}#{index}")
        for path in DOCUMENTS
        for index, block in enumerate(python_blocks(path), start=1)
    ),
    *(pytest.param(block, id=where) for where, block in DOCSTRING_EXAMPLES),
]
RUNNABLE_PAGES = [
    pytest.param(path, id=relative(path))
    for path in DOCUMENTS
    if path.read_text(encoding="utf-8").startswith(RUN_MARKER)
]
# Examples that call a real model provider are checked, but not executed.
OFFLINE_DOCSTRING_EXAMPLES = [
    pytest.param(block, id=where)
    for where, block in DOCSTRING_EXAMPLES
    if "init_chat_model(" not in block
]


@pytest.mark.parametrize("block", ALL_BLOCKS)
def test_code_blocks_use_the_real_public_api(block: str) -> None:
    tree = ast.parse(block)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "xstructured":
            for alias in node.names:
                assert alias.name in xstructured.__all__, (
                    f"unknown import {alias.name}"
                )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            target = CALLABLES.get(node.func.id)
            if target is None:
                continue
            parameters = inspect.signature(target).parameters
            accepts_any = any(
                p.kind is p.VAR_KEYWORD for p in parameters.values()
            )
            for keyword in node.keywords:
                if keyword.arg is not None and not accepts_any:
                    assert keyword.arg in parameters, (
                        f"{node.func.id}() has no {keyword.arg!r}"
                    )


@pytest.mark.parametrize("path", RUNNABLE_PAGES)
def test_runnable_pages_execute_offline(
    path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = ModuleType("docs_page")
    monkeypatch.setitem(sys.modules, module.__name__, module)
    for index, block in enumerate(python_blocks(path), start=1):
        code = compile(block, f"{relative(path)}#{index}", "exec")
        exec(code, module.__dict__)  # noqa: S102
    capsys.readouterr()


def test_some_pages_are_executed() -> None:
    assert len(RUNNABLE_PAGES) >= 5


@pytest.mark.parametrize("block", OFFLINE_DOCSTRING_EXAMPLES)
def test_docstring_examples_execute(
    block: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = ModuleType("docstring_example")
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(compile(block, module.__name__, "exec"), module.__dict__)  # noqa: S102
    capsys.readouterr()


def test_docstring_examples_are_found() -> None:
    assert len(DOCSTRING_EXAMPLES) >= 4
    assert len(OFFLINE_DOCSTRING_EXAMPLES) >= 3


@pytest.mark.parametrize("path", DOCUMENT_PARAMS)
def test_published_text_has_no_secrets_or_decision_records(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    assert re.search(r"\bxpl_[0-9a-f]{16,}", text) is None
    assert (
        re.search(
            r"\bADRs?\b|architecture decision record", text, re.IGNORECASE
        )
        is None
    )


@pytest.mark.parametrize("path", DOCUMENT_PARAMS)
def test_snippet_directives_are_well_formed(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, start=1):
        if SNIPPET_LIKE.search(line):
            include = INCLUDE.match(line.strip())
            where = f"{relative(path)}:{number}"
            assert include, f"{where} has a malformed snippet directive"
            assert ROOT.joinpath(include["path"]).is_file(), where


@pytest.mark.parametrize("path", DOCUMENT_PARAMS)
def test_code_blocks_fit_the_documentation_column(path: Path) -> None:
    too_wide = [
        f"{relative(path)}:{number} ({len(line)} columns)"
        for number, language, line in fenced_lines(path)
        if language not in WRAPPED_LANGUAGES and len(line) > CODE_WIDTH
    ]

    assert not too_wide


@pytest.mark.parametrize(
    "path", [pytest.param(path, id=relative(path)) for path in EXAMPLE_SCRIPTS]
)
def test_example_scripts_fit_the_documentation_column(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    too_wide = [
        f"{relative(path)}:{number} ({len(line)} columns)"
        for number, line in enumerate(lines, start=1)
        if len(line) > CODE_WIDTH
    ]

    assert not too_wide


def png_width(path: Path) -> int:
    header = path.read_bytes()[:24]
    assert header.startswith(b"\x89PNG\r\n\x1a\n"), path
    return int.from_bytes(header[16:20], "big")


def test_diagrams_are_shown_at_their_rendered_size() -> None:
    shown: set[str] = set()
    for path in ROOT.joinpath("docs").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        images = list(DIAGRAM_IMAGE.finditer(text))
        assert len(images) == text.count("assets/diagrams/"), relative(path)
        for image in images:
            where = f"{relative(path)}: {image['name']}"
            width = int(image["width"])
            rendered = png_width(DIAGRAMS / f"{image['name']}.png")
            assert abs(width * 2 - rendered) <= 1, where
            assert width <= MAX_DIAGRAM_WIDTH, where
            shown.add(image["name"])

    sources = ROOT.joinpath("diagrams").glob("*.mmd")
    assert shown == {source.stem for source in sources}
