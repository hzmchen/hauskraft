# SPDX-License-Identifier: MIT
"""M0S-E13-01 · Theme schema and the machine-readable theme contract files."""

from __future__ import annotations

import json

import pytest

from _support import FIXTURES
from _support.red import require_json
from _support.schemas import errors, load_json, validator
from _support.theme_contract import (
    CORE_ICON_NAMES, DESTRUCTIVE_PRIMARY_MIN_OKLAB, LAYOUT_OPTIONS, NON_TEXT_MIN, NON_TEXT_PAIRS, REQUIRED_TOKENS,
    TEXT_MIN, TEXT_PAIRS,
)

pytestmark = pytest.mark.story("M0S-E13-01")
SCHEMA = "theme/hauskraft.theme.schema.json"
EXPECTED = json.loads((FIXTURES / "themes" / "expected.json").read_text())["themes"]


@pytest.mark.parametrize("path", sorted((FIXTURES / "theme-json" / "valid").glob("*.json")), ids=lambda p: p.stem)
def test_valid_theme_json_passes(path) -> None:
    assert not errors(validator(SCHEMA, "M0S-E13-01"), load_json(path))


@pytest.mark.parametrize("path", sorted((FIXTURES / "theme-json" / "invalid").glob("*.json")), ids=lambda p: p.stem)
def test_invalid_theme_json_fails(path) -> None:
    doc = load_json(path)
    assert errors(validator(SCHEMA, "M0S-E13-01"), doc), doc.get("$comment")


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_fixture_package_theme_json(name: str) -> None:
    errs = errors(validator(SCHEMA, "M0S-E13-01"), load_json(FIXTURES / "themes" / name / "theme.json"))
    if "schema.invalid" in EXPECTED[name]["errors"]:
        assert errs, f"{name} must fail the theme schema"
    else:
        assert not errs, errs


def test_tokens_v1_lists_every_required_token() -> None:
    doc = require_json("packages/schemas/theme/tokens-v1.json", "M0S-E13-01")
    tokens = doc.get("tokens", {})
    assert set(tokens) == set(REQUIRED_TOKENS), {
        "missing": sorted(set(REQUIRED_TOKENS) - set(tokens)), "extra": sorted(set(tokens) - set(REQUIRED_TOKENS))}
    for name, ttype in REQUIRED_TOKENS.items():
        assert tokens[name].get("type") == ttype, f"{name}: expected $type {ttype}, got {tokens[name]}"


def test_tokens_v1_lists_contrast_rules() -> None:
    doc = require_json("packages/schemas/theme/tokens-v1.json", "M0S-E13-01")
    text = doc.get("contrast", {}).get("text", {})
    non_text = doc.get("contrast", {}).get("non_text", {})
    assert text.get("min") == TEXT_MIN and non_text.get("min") == NON_TEXT_MIN
    assert {tuple(p) for p in text.get("pairs", [])} == set(TEXT_PAIRS)
    assert {tuple(p) for p in non_text.get("pairs", [])} == set(NON_TEXT_PAIRS)
    assert doc.get("distinct", {}).get("destructive_primary_min_oklab") == DESTRUCTIVE_PRIMARY_MIN_OKLAB


def test_icon_names_v1() -> None:
    doc = require_json("packages/schemas/theme/icon-names-v1.json", "M0S-E13-01")
    assert doc.get("icons") == CORE_ICON_NAMES


def test_layout_options_v1() -> None:
    doc = require_json("packages/schemas/theme/layout-options-v1.json", "M0S-E13-01")
    for key, values in LAYOUT_OPTIONS.items():
        assert doc.get(key) == values, f"{key}: expected {values}, got {doc.get(key)}"
