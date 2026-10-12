# SPDX-License-Identifier: MIT
"""Lenient readers for config files (JSONC, TOML, YAML) used by static acceptance tests."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

import yaml

from .red import require_file


def _strip_jsonc(text: str) -> str:
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1]); i += 2; continue
            if ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True; out.append(ch)
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        else:
            out.append(ch)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def jsonc(rel: str, story: str) -> Any:
    return json.loads(_strip_jsonc(require_file(rel, story).read_text(encoding="utf-8")))


def toml(rel: str, story: str) -> dict[str, Any]:
    return tomllib.loads(require_file(rel, story).read_text(encoding="utf-8"))


def yaml_doc(rel: str, story: str) -> Any:
    return yaml.safe_load(require_file(rel, story).read_text(encoding="utf-8"))


def dig(data: Any, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if not isinstance(data, dict) or k not in data:
            return default
        data = data[k]
    return data


def text_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file() and p.suffix in suffixes and "node_modules" not in p.parts]
