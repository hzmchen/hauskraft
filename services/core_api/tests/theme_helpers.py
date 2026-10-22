# SPDX-License-Identifier: AGPL-3.0-or-later
"""A stand-in for the built-in Default theme, so tests do not depend on the real built-in themes."""

import json
import shutil
from pathlib import Path

from hauskraft_core.themes.registry import BUILTIN_DEFAULT

FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "themes"


def builtin_default(root: Path, source: str = "valid-minimal") -> Path:
    """Copy a fixture to ``root/builtin/default`` posing as Default; returns the ``builtin`` theme path."""
    folder = root / "builtin" / "default"
    shutil.copytree(FIXTURES / source, folder)
    manifest_path = folder / "hauskraft.plugin.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["id"] = BUILTIN_DEFAULT
    manifest_path.write_text(json.dumps(manifest))
    return root / "builtin"
