# SPDX-License-Identifier: MIT
"""Load the project's JSON Schemas (packages/schemas) for fixture-based contract tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from . import REPO
from .red import require_json

SCHEMAS = REPO / "packages" / "schemas"


def _registry() -> Registry:
    """Register every schema under packages/schemas by its $id so $refs resolve offline."""
    resources = []
    for path in SCHEMAS.rglob("*.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(doc, dict) and "$id" in doc:
            resources.append((doc["$id"], Resource.from_contents(doc)))
    return Registry().with_resources(resources)


def validator(rel: str, story: str) -> Draft202012Validator:
    schema = require_json(f"packages/schemas/{rel}", story)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=_registry())


def errors(v: Draft202012Validator, instance: Any) -> list[str]:
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in v.iter_errors(instance)]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
