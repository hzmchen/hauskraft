# SPDX-License-Identifier: MIT
"""M0S-E01-03: plugin web code may import only the SDK, the UI kit and a few React libraries.

Runs ESLint on stdin as if each probe lived inside a plugin's web package.
"""

from __future__ import annotations

import json
import subprocess

import pytest
from _support import REPO

pytestmark = pytest.mark.story("M0S-E01-03")

PLUGIN_FILE = "plugins/official/tasks/web/src/widgets/_probe.tsx"
RULES = {"no-restricted-imports", "import/no-restricted-paths"}


def _rules(source: str, as_path: str = PLUGIN_FILE) -> set[str]:
    eslint = REPO / "node_modules" / ".bin" / "eslint"
    assert eslint.exists(), "run `pnpm install` first"
    proc = subprocess.run(
        [str(eslint), "--format", "json", "--stdin", "--stdin-filename", as_path],
        cwd=REPO,
        input=source,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in (0, 1), proc.stderr
    return {m.get("ruleId") for r in json.loads(proc.stdout or "[]") for m in r.get("messages", [])}


@pytest.mark.parametrize(
    "module",
    [
        "@hauskraft/sdk-ts",
        "@hauskraft/ui",
        "@hauskraft/ui/widget",
        "react",
        "react-dom/client",
        "react-i18next",
        "@tanstack/react-query",
        "./components/TaskRow",
        "../locales/en/tasks.json",
    ],
)
def test_allowed_imports(module: str) -> None:
    assert not _rules(f'import x from "{module}";\nexport const y = x;\n') & RULES


@pytest.mark.parametrize(
    "module",
    [
        "../../../../../apps/web/src/shell/nav/SidebarNav",
        "lodash",
        "@tanstack/react-router",
        "axios",
    ],
)
def test_disallowed_imports(module: str) -> None:
    assert _rules(f'import x from "{module}";\nexport const y = x;\n') & RULES


def test_rule_does_not_apply_to_the_app_shell() -> None:
    src = 'import { createRouter } from "@tanstack/react-router";\nexport const r = createRouter;\n'
    assert not _rules(src, "apps/web/src/router.tsx") & RULES
