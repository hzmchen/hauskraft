# SPDX-License-Identifier: MIT
"""M2S-E05-01 · the SKILL.md frontmatter schema (ADR 0023); M2S-E05-03/04 · the tasks plugin's two skills.

Fixtures: tests/fixtures/skills/{valid,invalid}/*.SKILL.md; each invalid fixture's description names the broken rule.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from _support import FIXTURES, REPO
from _support.schemas import errors, validator

story = pytest.mark.story
STORY = "M2S-E05-01"
SCHEMA = "skill/skill.schema.json"
ROOT = FIXTURES / "skills"
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n(.+)", re.S)


def frontmatter(path: Path) -> tuple[dict, str]:
    m = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    assert m, f"{path} has no YAML frontmatter"
    return yaml.safe_load(m.group(1)), m.group(2)


@story(STORY)
def test_schema_has_a_stable_id() -> None:
    v = validator(SCHEMA, STORY)
    assert v.schema["$id"] == "https://hauskraft.dev/schema/skill/v1.json"
    assert v.schema.get("additionalProperties") is False


@story(STORY)
@pytest.mark.parametrize("path", sorted((ROOT / "valid").glob("*.SKILL.md")), ids=lambda p: p.name)
def test_valid_skill_passes(path: Path) -> None:
    meta, body = frontmatter(path)
    assert not errors(validator(SCHEMA, STORY), meta)
    assert body.strip(), "the body holds the instructions"


@story(STORY)
@pytest.mark.parametrize("path", sorted((ROOT / "invalid").glob("*.SKILL.md")), ids=lambda p: p.name)
def test_invalid_skill_fails(path: Path) -> None:
    meta, _ = frontmatter(path)
    assert errors(validator(SCHEMA, STORY), meta), f"{path.name} should be rejected"


@pytest.mark.parametrize(("skill", "tools", "output"), [
    pytest.param("add-from-text", [], "schema", marks=story("M2S-E05-03"), id="add-from-text"),
    pytest.param("weekly-overview", ["tasks.list"], "text", marks=story("M2S-E05-04"), id="weekly-overview"),
])
def test_tasks_plugin_ships_its_skills(skill: str, tools: list[str], output: str) -> None:
    path = REPO / "plugins" / "official" / "tasks" / "skills" / skill / "SKILL.md"
    if not path.exists():
        pytest.fail(f"RED: {path.relative_to(REPO)} does not exist yet", pytrace=False)
    meta, body = frontmatter(path)
    assert not errors(validator(SCHEMA, STORY), meta)
    assert meta["tools"] == tools
    assert (meta["output"] == "text") if output == "text" else ("schema" in meta["output"])
    if skill == "add-from-text":
        assert re.search(r"(?i)\bdata\b", body) and re.search(r"(?i)instruction", body), \
            "the instructions say the pasted text is data, never instructions"
