# SPDX-License-Identifier: MIT
"""M0S-E02-02: every hauskraft.plugin.json in the repository validates against the manifest schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

pytestmark = pytest.mark.contract

SCHEMAS = Path(__file__).resolve().parents[1]
REPO = SCHEMAS.parents[1]
MANIFEST_ROOTS = ["plugins", "themes"]
MANIFESTS = sorted(
    p for root in MANIFEST_ROOTS for p in (REPO / root).rglob("hauskraft.plugin.json") if "node_modules" not in p.parts
)


def _validator() -> Draft202012Validator:
    resources = [
        (d["$id"], Resource.from_contents(d))
        for d in (json.loads(p.read_text()) for p in SCHEMAS.rglob("*.schema.json"))
    ]
    schema = json.loads((SCHEMAS / "manifest" / "hauskraft.plugin.schema.json").read_text())
    return Draft202012Validator(schema, registry=Registry().with_resources(resources))


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: str(p.parent.relative_to(REPO)))
def test_manifest_is_valid(path: Path) -> None:
    errors = [
        f"{'/'.join(map(str, e.absolute_path))}: {e.message}"
        for e in _validator().iter_errors(json.loads(path.read_text()))
    ]
    assert errors == []


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: str(p.parent.relative_to(REPO)))
def test_manifest_id_is_unique(path: Path) -> None:
    ids = [json.loads(p.read_text())["id"] for p in MANIFESTS]
    assert ids.count(json.loads(path.read_text())["id"]) == 1
