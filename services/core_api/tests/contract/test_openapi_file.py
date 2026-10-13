# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E03-05: the committed OpenAPI file is exactly what the app generates."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[4]
OPENAPI = REPO / "packages" / "schemas" / "openapi" / "core-api.openapi.json"
SCRIPT = REPO / "scripts" / "export_openapi.py"


def test_committed_file_matches_the_app() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"], cwd=REPO, capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_export_is_deterministic(tmp_path: Path) -> None:
    outputs = []
    for i in range(2):
        target = tmp_path / f"{i}.json"
        subprocess.run(
            [sys.executable, str(SCRIPT), "--output", str(target)], cwd=REPO, check=True, capture_output=True
        )
        outputs.append(target.read_bytes())
    assert outputs[0] == outputs[1]


def test_contract_shape() -> None:
    doc = json.loads(OPENAPI.read_text())
    assert doc["openapi"].startswith("3.1")
    ops = [op["operationId"] for item in doc["paths"].values() for op in item.values() if isinstance(op, dict)]
    assert len(ops) == len(set(ops)), "operation ids must be unique"
    assert all(p.startswith("/api/v1/") for p in doc["paths"])
    assert {op.split("_", 1)[0] for op in ops} >= {"health", "auth", "users", "plugins", "tasks"}
    text = OPENAPI.read_text()
    assert text == json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n", "sorted keys"
