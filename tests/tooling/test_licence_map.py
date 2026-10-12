# SPDX-License-Identifier: MIT
"""M0S-E02-04: scripts/check-licence-map.py enforces the licence map from spec §4.2."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from _support import REPO

pytestmark = pytest.mark.story("M0S-E02-04")

SCRIPT = REPO / "scripts" / "check-licence-map.py"


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    assert SCRIPT.exists(), "scripts/check-licence-map.py missing"
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)], capture_output=True, text=True, check=False
    )


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_headers_in_the_right_places_pass(tmp_path: Path) -> None:
    _write(tmp_path, "services/core_api/app.py", "# SPDX-License-Identifier: AGPL-3.0-or-later\n")
    _write(tmp_path, "apps/web/src/main.ts", "// SPDX-License-Identifier: AGPL-3.0-or-later\n")
    _write(tmp_path, "packages/sdk-py/sdk.py", "# SPDX-License-Identifier: MIT\n")
    _write(tmp_path, "plugins/official/tasks/web/x.tsx", "// SPDX-License-Identifier: MIT\n")
    _write(tmp_path, "integrations/ha-hearthos/README.md", "<!-- SPDX-License-Identifier: MIT -->\n")
    _write(tmp_path, "docs/anything.md", "no rule here\n")
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_every_offender_is_listed(tmp_path: Path) -> None:
    _write(tmp_path, "services/core_api/app.py", "# SPDX-License-Identifier: MIT\n")
    _write(tmp_path, "packages/ui/index.ts", "// SPDX-License-Identifier: AGPL-3.0-or-later\n")
    _write(tmp_path, "themes/builtin/x/theme.json", "{}\n")  # no licence at all
    proc = _run(tmp_path)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 1
    for rel in ("services/core_api/app.py", "packages/ui/index.ts", "themes/builtin/x/theme.json"):
        assert rel in out, out


def test_reuse_toml_annotations_count(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "REUSE.toml",
        (
            "version = 1\n"
            '[[annotations]]\npath = "**"\nprecedence = "aggregate"\n'
            'SPDX-FileCopyrightText = "x"\nSPDX-License-Identifier = "AGPL-3.0-or-later"\n'
            '[[annotations]]\npath = ["packages/**", "themes/**"]\nprecedence = "aggregate"\n'
            'SPDX-FileCopyrightText = "x"\nSPDX-License-Identifier = "MIT"\n'
            '[[annotations]]\npath = "themes/**/assets/fonts/**"\nprecedence = "override"\n'
            'SPDX-FileCopyrightText = "x"\nSPDX-License-Identifier = "OFL-1.1"\n'
        ),
    )
    _write(tmp_path, "packages/ui/package.json", "{}\n")
    _write(tmp_path, "services/core_api/pyproject.toml", "[project]\n")
    (tmp_path / "themes/builtin/x/assets/fonts").mkdir(parents=True)
    (tmp_path / "themes/builtin/x/assets/fonts/A.woff2").write_bytes(b"wOF2\x00\x01")
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_fonts_must_be_ofl(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "REUSE.toml",
        (
            'version = 1\n[[annotations]]\npath = "themes/**"\nSPDX-FileCopyrightText = "x"\n'
            'SPDX-License-Identifier = "MIT"\n'
        ),
    )
    (tmp_path / "themes/builtin/x/assets/fonts").mkdir(parents=True)
    (tmp_path / "themes/builtin/x/assets/fonts/A.woff2").write_bytes(b"wOF2\x00\x01")
    proc = _run(tmp_path)
    assert proc.returncode == 1
    assert "themes/builtin/x/assets/fonts/A.woff2" in proc.stdout + proc.stderr


def test_licence_files_and_vendored_folders_are_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "packages/ui/LICENSE", "MIT License\n")
    _write(tmp_path, "packages/ui/node_modules/dep/index.js", "// SPDX-License-Identifier: GPL-3.0-only\n")
    _write(tmp_path, "packages/ui/src/index.ts", "// SPDX-License-Identifier: MIT\n")
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_repository_itself_passes() -> None:
    proc = _run(REPO)
    assert proc.returncode == 0, proc.stdout + proc.stderr
