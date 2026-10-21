# SPDX-License-Identifier: AGPL-3.0-or-later
"""Access to the MIT JSON Schemas in ``packages/schemas`` (manifest, events, theme).

``HAUSKRAFT_SCHEMAS_DIR`` overrides the location (the container image copies the folder next to the app).
"""

from __future__ import annotations

import json
import os
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

DEFAULT_SCHEMAS_DIR = Path(__file__).resolve().parents[4] / "packages" / "schemas"


def schemas_dir() -> Path:
    return Path(os.environ.get("HAUSKRAFT_SCHEMAS_DIR") or DEFAULT_SCHEMAS_DIR)


@cache
def _registry() -> Registry:
    resources = []
    for path in schemas_dir().rglob("*.schema.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        resources.append((doc["$id"], Resource.from_contents(doc)))
    return Registry().with_resources(resources)


@cache
def load(rel: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((schemas_dir() / rel).read_text(encoding="utf-8"))
    return data


def exists(rel: str) -> bool:
    return (schemas_dir() / rel).is_file()


@cache
def validator(rel: str) -> Draft202012Validator:
    return Draft202012Validator(load(rel), registry=_registry(), format_checker=Draft202012Validator.FORMAT_CHECKER)


def errors(rel: str, instance: Any) -> list[str]:
    return [
        f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in validator(rel).iter_errors(instance)
    ]
