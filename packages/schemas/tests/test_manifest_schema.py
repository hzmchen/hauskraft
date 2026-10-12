# SPDX-License-Identifier: MIT
"""M0S-E06-01 contract tests: the plugin manifest schema against its own valid/invalid fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

pytestmark = pytest.mark.contract

SCHEMAS = Path(__file__).resolve().parents[1]
SPDX_MIT = "SPDX-" + "License-Identifier: MIT"  # split so REUSE does not read it as this file's tag
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "manifest"


def _validator(rel: str) -> Draft202012Validator:
    resources = []
    for path in SCHEMAS.rglob("*.schema.json"):
        doc = json.loads(path.read_text())
        resources.append((doc["$id"], Resource.from_contents(doc)))
    schema = json.loads((SCHEMAS / rel).read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=Registry().with_resources(resources))


MANIFEST = _validator("manifest/hearthos.plugin.schema.json") if (SCHEMAS / "manifest").exists() else None


def _errors(doc: object) -> list[str]:
    assert MANIFEST is not None, "packages/schemas/manifest/hearthos.plugin.schema.json missing"
    return [e.message for e in MANIFEST.iter_errors(doc)]


@pytest.mark.parametrize("path", sorted((FIXTURES / "valid").glob("*.json")), ids=lambda p: p.stem)
def test_valid(path: Path) -> None:
    assert _errors(json.loads(path.read_text())) == []


@pytest.mark.parametrize("path", sorted((FIXTURES / "invalid").glob("*.json")), ids=lambda p: p.stem)
def test_invalid(path: Path) -> None:
    doc = json.loads(path.read_text())
    assert _errors(doc), f"{path.name} must be rejected: {doc['$comment']}"


def test_every_schema_has_an_id_and_spdx_comment() -> None:
    for path in SCHEMAS.rglob("*.schema.json"):
        doc = json.loads(path.read_text())
        assert doc["$schema"] == "https://json-schema.org/draft/2020-12/schema", path
        assert doc["$id"].startswith("https://hearthos.dev/schema/"), path
        assert doc.get("$comment") == SPDX_MIT, path
