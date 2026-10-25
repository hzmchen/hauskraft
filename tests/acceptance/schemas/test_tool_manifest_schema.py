# SPDX-License-Identifier: MIT
"""M2S-E02-01 · tools, skills and agent guidance in the plugin manifest schema (spec §5.3, ADR 0019, ADR 0023).

Fixtures: tests/fixtures/manifests/tools/. Each invalid fixture breaks one rule, named in its $comment.
"""

from __future__ import annotations

import pytest

from _support import FIXTURES, REPO
from _support.schemas import errors, load_json, validator

pytestmark = pytest.mark.story("M2S-E02-01")
STORY = "M2S-E02-01"
SCHEMA = "manifest/hauskraft.plugin.schema.json"
ROOT = FIXTURES / "manifests" / "tools"


def _v():
    return validator(SCHEMA, STORY)


@pytest.mark.parametrize("path", sorted((ROOT / "valid").glob("*.json")), ids=lambda p: p.stem)
def test_valid_fixture_passes(path) -> None:
    assert not errors(_v(), load_json(path))


@pytest.mark.parametrize("path", sorted((ROOT / "invalid").glob("*.json")), ids=lambda p: p.stem)
def test_invalid_fixture_fails(path) -> None:
    doc = load_json(path)
    assert errors(_v(), doc), f"{path.name} should be rejected: {doc['$comment']}"


def test_tool_definition_names_the_m2_fields() -> None:
    tool = _v().schema["$defs"]["tool"]
    assert {"name", "description", "annotations", "data_class", "permission", "agent"} <= set(tool["properties"])


@pytest.mark.parametrize("rel", [
    "plugins/official/tasks/hauskraft.plugin.json",
    "tests/fixtures/manifests/valid/tasks.json",
    "tests/fixtures/manifests/valid/connector-paperless.json",
    "tests/fixtures/manifests/valid/theme.json",
])
def test_existing_manifests_still_pass(rel: str) -> None:
    assert not errors(_v(), load_json(REPO / rel))
