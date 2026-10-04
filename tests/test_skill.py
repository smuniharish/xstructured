"""The Agent Skill follows the Agent Skills specification and stays self-contained."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

SKILL = Path(__file__).resolve().parent.parent / "skills" / "xstructured"
ALLOWED_KEYS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
LINK = re.compile(r"\]\((?P<target>[^)#\s]+)(?:#[^)]*)?\)")
FILES = [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]


def frontmatter_and_body() -> tuple[dict[str, object], str]:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    _, header, body = text.split("---\n", 2)
    return yaml.safe_load(header), body


def test_frontmatter_follows_the_specification() -> None:
    meta, _ = frontmatter_and_body()

    assert set(meta) <= ALLOWED_KEYS
    name = meta["name"]
    assert isinstance(name, str)
    assert name == SKILL.name
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name)
    assert len(name) <= 64
    description = meta["description"]
    assert isinstance(description, str)
    assert 1 <= len(description) <= 1024
    assert "Use when" in description
    compatibility = meta["compatibility"]
    assert isinstance(compatibility, str)
    assert len(compatibility) <= 500
    metadata = meta["metadata"]
    assert isinstance(metadata, dict)
    assert all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in metadata.items()
    )


def test_skill_body_is_concise() -> None:
    _, body = frontmatter_and_body()

    assert len(body.splitlines()) < 500


@pytest.mark.parametrize("path", FILES, ids=lambda path: path.name)
def test_relative_links_stay_inside_the_skill(path: Path) -> None:
    for match in LINK.finditer(path.read_text(encoding="utf-8")):
        target = match.group("target")
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (path.parent / target).resolve()
        assert resolved.is_file(), f"{path.name} links to missing {target}"
        assert resolved.is_relative_to(SKILL), (
            f"{path.name} links outside the skill: {target}"
        )


def test_every_reference_is_linked_from_the_skill() -> None:
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")

    for reference in (SKILL / "references").glob("*.md"):
        assert f"references/{reference.name}" in skill
