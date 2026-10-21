# SPDX-License-Identifier: AGPL-3.0-or-later
"""Find plugin manifests (``<path>/*/hauskraft.plugin.json``) under the configured plugin and theme paths."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MANIFEST_FILE = "hauskraft.plugin.json"


@dataclass(frozen=True)
class DiscoveredManifest:
    folder: Path
    manifest: dict[str, Any] = field(default_factory=dict)
    sha256: str = ""
    error: str | None = None

    @property
    def id(self) -> str:
        return str(self.manifest.get("id") or self.folder.name)

    @property
    def runtime(self) -> dict[str, Any]:
        runtime = self.manifest.get("runtime")
        return runtime if isinstance(runtime, dict) else {}


def discover(paths: Iterable[Path]) -> list[DiscoveredManifest]:
    """Every direct subfolder of each path that holds a manifest, in a stable order."""
    found: list[DiscoveredManifest] = []
    for root in paths:
        if not root.is_dir():
            continue
        for manifest_path in sorted(root.glob(f"*/{MANIFEST_FILE}")):
            raw = manifest_path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                found.append(DiscoveredManifest(manifest_path.parent, {}, digest, f"invalid JSON: {exc}"))
                continue
            if not isinstance(data, dict):
                found.append(DiscoveredManifest(manifest_path.parent, {}, digest, "manifest is not a JSON object"))
                continue
            found.append(DiscoveredManifest(manifest_path.parent, data, digest))
    return found
