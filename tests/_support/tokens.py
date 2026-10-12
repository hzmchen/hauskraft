# SPDX-License-Identifier: MIT
"""Minimal DTCG token-file reader for the acceptance suite (flatten + alias resolution)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_ALIAS = re.compile(r"^\{([A-Za-z0-9_.\-]+)\}$")


def flatten(tree: dict[str, Any], prefix: str = "", inherited_type: str | None = None) -> dict[str, dict[str, Any]]:
    """Return {"group.token": {"$type": ..., "$value": ...}} for every token in a DTCG tree."""
    out: dict[str, dict[str, Any]] = {}
    group_type = tree.get("$type", inherited_type)
    for key, node in tree.items():
        if key.startswith("$") or not isinstance(node, dict):
            continue
        name = f"{prefix}.{key}" if prefix else key
        if "$value" in node:
            out[name] = {"$type": node.get("$type", group_type), "$value": node["$value"]}
        else:
            out.update(flatten(node, name, group_type))
    return out


def load(path: Path) -> dict[str, dict[str, Any]]:
    return flatten(json.loads(path.read_text(encoding="utf-8")))


def resolve(tokens: dict[str, dict[str, Any]], name: str, _seen: tuple[str, ...] = ()) -> Any:
    """Resolve a token's value, following "{group.token}" aliases. Raises on cycles or misses."""
    if name in _seen:
        raise ValueError(f"alias cycle: {' -> '.join((*_seen, name))}")
    if name not in tokens:
        raise KeyError(name)
    value = tokens[name]["$value"]
    if isinstance(value, str):
        m = _ALIAS.match(value)
        if m:
            return resolve(tokens, m.group(1), (*_seen, name))
    return value
