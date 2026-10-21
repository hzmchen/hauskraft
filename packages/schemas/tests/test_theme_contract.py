# SPDX-License-Identifier: MIT
"""M0S-E13-01 contract tests: theme.json schema, the contract data files and the generated types."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

pytestmark = pytest.mark.contract

SCHEMAS = Path(__file__).resolve().parents[1]
REPO = SCHEMAS.parents[1]
THEME = SCHEMAS / "theme"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "theme"


def _validator() -> Draft202012Validator:
    resources = [
        (d["$id"], Resource.from_contents(d))
        for d in (json.loads(p.read_text()) for p in SCHEMAS.rglob("*.schema.json"))
    ]
    schema = json.loads((THEME / "hauskraft.theme.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=Registry().with_resources(resources))


def _load(name: str) -> dict:
    return json.loads((THEME / name).read_text())


@pytest.mark.parametrize("path", sorted((FIXTURES / "valid").glob("*.json")), ids=lambda p: p.stem)
def test_valid(path: Path) -> None:
    assert [e.message for e in _validator().iter_errors(json.loads(path.read_text()))] == []


@pytest.mark.parametrize("path", sorted((FIXTURES / "invalid").glob("*.json")), ids=lambda p: p.stem)
def test_invalid(path: Path) -> None:
    doc = json.loads(path.read_text())
    assert list(_validator().iter_errors(doc)), doc["$comment"]


def test_schema_enums_match_layout_options() -> None:
    options = _load("layout-options-v1.json")
    defs = _load("hauskraft.theme.schema.json")["$defs"]
    for key, values in options.items():
        if key.startswith("$"):
            continue
        assert defs["enum." + key]["enum"] == values, key


def test_contract_files_reference_adr_0013() -> None:
    for name in ("tokens-v1.json", "icon-names-v1.json", "layout-options-v1.json", "hauskraft.theme.schema.json"):
        assert "ADR-0013" in json.dumps(_load(name)), name


def test_font_limit_matches_tokens_v1() -> None:
    limits = _load("tokens-v1.json")["limits"]
    assert _load("hauskraft.theme.schema.json")["properties"]["fonts"]["maxItems"] == limits["max_fonts"]


def test_generated_types_are_current() -> None:
    node = shutil.which("node")
    assert node, "node is required to check the TypeScript generator"
    ts = subprocess.run(
        [node, str(REPO / "scripts" / "gen-theme-types.mjs"), "--check"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ts.returncode == 0, ts.stdout + ts.stderr
    py = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "gen_theme_types.py"), "--check"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert py.returncode == 0, py.stdout + py.stderr


def test_python_literal_lists_every_icon() -> None:
    from typing import get_args

    from hauskraft_sdk.theme_contract import CORE_ICON_NAMES, IconName

    assert list(get_args(IconName)) == _load("icon-names-v1.json")["icons"] == list(CORE_ICON_NAMES)
