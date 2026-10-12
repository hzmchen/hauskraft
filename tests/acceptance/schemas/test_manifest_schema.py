# SPDX-License-Identifier: MIT
"""M0S-E06-01 · Plugin manifest JSON Schema, checked against owned fixtures."""

from __future__ import annotations

import json

import pytest

from _support import FIXTURES, REPO
from _support.schemas import errors, load_json, validator

pytestmark = pytest.mark.story("M0S-E06-01")
SCHEMA = "manifest/hearthos.plugin.schema.json"

EXPECTED = json.loads((FIXTURES / "themes" / "expected.json").read_text())["themes"]
THEME_MANIFESTS_OK = [n for n, e in EXPECTED.items() if "manifest.invalid" not in e["errors"]]


@pytest.mark.parametrize("path", sorted((FIXTURES / "manifests" / "valid").glob("*.json")), ids=lambda p: p.stem)
def test_valid_manifest_fixture_passes(path) -> None:
    errs = errors(validator(SCHEMA, "M0S-E06-01"), load_json(path))
    assert not errs, errs


@pytest.mark.parametrize("path", sorted((FIXTURES / "manifests" / "invalid").glob("*.json")), ids=lambda p: p.stem)
def test_invalid_manifest_fixture_fails(path) -> None:
    doc = load_json(path)
    errs = errors(validator(SCHEMA, "M0S-E06-01"), doc)
    assert errs, f"{path.name} should be rejected: {doc.get('$comment')}"


@pytest.mark.parametrize("name", THEME_MANIFESTS_OK)
def test_fixture_theme_manifests_pass(name: str) -> None:
    errs = errors(validator(SCHEMA, "M0S-E06-01"), load_json(FIXTURES / "themes" / name / "hearthos.plugin.json"))
    assert not errs, errs


def test_theme_manifest_with_capabilities_fails() -> None:
    doc = load_json(FIXTURES / "themes" / "invalid-manifest-capabilities" / "hearthos.plugin.json")
    assert errors(validator(SCHEMA, "M0S-E06-01"), doc)


@pytest.mark.parametrize("kind", ["container", "subprocess", "wasm", "inprocess", "declarative"])
def test_all_runtime_kinds_are_accepted(kind: str) -> None:
    doc = load_json(FIXTURES / "manifests" / "valid" / "connector-paperless.json")
    doc["runtime"]["kind"] = kind
    assert not errors(validator(SCHEMA, "M0S-E06-01"), doc)


@pytest.mark.parametrize("data_class", ["public", "household", "personal", "financial", "tenant", "child",
                                        "health", "secret"])
def test_all_data_classes_are_accepted(data_class: str) -> None:
    doc = load_json(FIXTURES / "manifests" / "valid" / "tasks.json")
    doc["data_classes"]["reads"] = [data_class]
    assert not errors(validator(SCHEMA, "M0S-E06-01"), doc)


@pytest.mark.story("M0S-E07-01")
def test_real_tasks_manifest_passes() -> None:
    path = REPO / "plugins" / "official" / "tasks" / "hearthos.plugin.json"
    if not path.exists():
        pytest.fail("RED (M0S-E07-01): plugins/official/tasks/hearthos.plugin.json missing", pytrace=False)
    doc = load_json(path)
    assert not errors(validator(SCHEMA, "M0S-E06-01"), doc)
    assert doc["id"] == "org.hearthos.tasks" and doc["license"] == "MIT"
    assert doc["runtime"]["kind"] == "inprocess"
