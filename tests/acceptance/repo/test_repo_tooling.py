# SPDX-License-Identifier: MIT
"""E01 · Repo & tooling. Static checks on workspace layout and tool configuration."""

from __future__ import annotations

import re

import pytest

from _support import FIXTURES, REPO
from _support.files import dig, jsonc, toml, yaml_doc
from _support.red import require_file, require_text
from _support.tools import eslint_on_stdin, ruff_on_stdin

story = pytest.mark.story


# ---------------------------------------------------------------- M0S-E01-01 workspaces
@story("M0S-E01-01")
@pytest.mark.parametrize("rel", [
    "pyproject.toml", "uv.lock", ".python-version", "package.json", "pnpm-workspace.yaml",
    "pnpm-lock.yaml", ".node-version", "compose.yaml",
])
def test_workspace_root_file_exists(rel: str) -> None:
    require_file(rel, "M0S-E01-01")


@story("M0S-E01-01")
def test_python_and_node_versions_are_pinned() -> None:
    assert require_text(".python-version", "M0S-E01-01").strip() == "3.13"
    assert require_text(".node-version", "M0S-E01-01").strip().split(".")[0] == "24"


@story("M0S-E01-01")
def test_uv_workspace_members() -> None:
    members = dig(toml("pyproject.toml", "M0S-E01-01"), "tool", "uv", "workspace", "members", default=[])
    for expected in ("services/core_api", "packages/sdk-py", "plugins/official/tasks/backend"):
        assert expected in members, f"uv workspace is missing {expected}: {members}"


@story("M0S-E01-01")
def test_pnpm_workspace_packages() -> None:
    pkgs = (yaml_doc("pnpm-workspace.yaml", "M0S-E01-01") or {}).get("packages", [])
    for expected in ("apps/*", "packages/sdk-ts", "packages/ui", "plugins/official/*/web", "tests/e2e"):
        assert expected in pkgs, f"pnpm workspace is missing {expected}: {pkgs}"


@story("M0S-E01-01")
def test_package_manager_is_declared() -> None:
    pm = jsonc("package.json", "M0S-E01-01").get("packageManager", "")
    assert pm.startswith("pnpm@"), f"package.json packageManager should pin pnpm, got {pm!r}"


@story("M0S-E01-01")
@pytest.mark.parametrize("service", ["gateway", "agents", "workflows", "plugin_host"])
def test_later_services_are_placeholders(service: str) -> None:
    text = require_text(f"services/{service}/README.md", "M0S-E01-01")
    assert "M1" in text or "M2" in text or "M5" in text, "placeholder must say which milestone owns it"


@story("M0S-E01-01")
@pytest.mark.parametrize("rel", ["themes/builtin", "themes/template"])
def test_theme_folders_exist(rel: str) -> None:
    assert (REPO / rel).is_dir(), f"RED (M0S-E01-01): {rel}/ missing"


# ---------------------------------------------------------------- M0S-E01-02 python tooling
@story("M0S-E01-02")
def test_ruff_mypy_pytest_configured() -> None:
    cfg = toml("pyproject.toml", "M0S-E01-02")
    select = set(dig(cfg, "tool", "ruff", "lint", "select", default=[]))
    for rule in ("E", "F", "I", "UP", "B", "S", "ASYNC", "PT", "RUF", "TID"):
        assert rule in select, f"ruff lint.select is missing {rule}"
    assert dig(cfg, "tool", "mypy", "strict") is True, "mypy must run in strict mode"
    assert "pydantic.mypy" in dig(cfg, "tool", "mypy", "plugins", default=[])
    markers = " ".join(dig(cfg, "tool", "pytest", "ini_options", "markers", default=[]))
    for m in ("unit", "integration", "contract"):
        assert re.search(rf"\b{m}\b", markers), f"pytest marker {m!r} not registered"


@story("M0S-E01-02")
def test_plugins_cannot_import_core_internals() -> None:
    src = (FIXTURES / "python" / "plugin_imports_core.py").read_text()
    findings = ruff_on_stdin(src, "plugins/official/tasks/backend/src/hauskraft_tasks/_probe.py", "M0S-E01-02")
    assert any(f["code"] == "TID251" for f in findings), f"expected TID251, got {findings}"


@story("M0S-E01-02")
def test_core_may_import_itself() -> None:
    src = (FIXTURES / "python" / "core_imports_core.py").read_text()
    findings = ruff_on_stdin(src, "services/core_api/src/hauskraft_core/_probe.py", "M0S-E01-02")
    assert not any(f["code"] == "TID251" for f in findings), findings


# ---------------------------------------------------------------- M0S-E01-03 typescript tooling
@story("M0S-E01-03")
def test_tsconfig_base_is_strict() -> None:
    opts = jsonc("tsconfig.base.json", "M0S-E01-03").get("compilerOptions", {})
    assert opts.get("strict") is True
    assert str(opts.get("moduleResolution", "")).lower() == "bundler"
    assert opts.get("verbatimModuleSyntax") is True


@story("M0S-E01-03")
def test_typescript_is_pinned_to_6_0() -> None:
    pkg = jsonc("package.json", "M0S-E01-03")
    version = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}.get("typescript", "")
    assert version.startswith("~6.0"), f"typescript should be ~6.0 (ADR-0011), got {version!r}"


@story("M0S-E01-03")
def test_plugin_web_cannot_import_app_shell() -> None:
    src = (FIXTURES / "lint" / "plugin-imports-app.tsx").read_text()
    msgs = eslint_on_stdin(src, "plugins/official/tasks/web/src/_probe.tsx", "M0S-E01-03")
    assert any(m.get("ruleId") in ("no-restricted-imports", "import/no-restricted-paths") for m in msgs), msgs


# ---------------------------------------------------------------- M0S-E01-04 justfile, pre-commit
JUST_RECIPES = ["setup", "dev", "db", "lint", "fmt", "typecheck", "test", "test-int", "contract", "gen",
                "e2e", "invariance", "acceptance", "demo", "themes-validate", "check"]


@story("M0S-E01-04")
@pytest.mark.parametrize("recipe", JUST_RECIPES)
def test_justfile_has_recipe(recipe: str) -> None:
    text = require_text("justfile", "M0S-E01-04")
    assert re.search(rf"^@?{re.escape(recipe)}(\s[^:=]*)?:(?!=)", text, re.M), f"justfile lacks recipe {recipe!r}"


@story("M0S-E01-04")
def test_pre_commit_hooks() -> None:
    cfg = yaml_doc(".pre-commit-config.yaml", "M0S-E01-04") or {}
    ids = {h.get("id") for repo in cfg.get("repos", []) for h in repo.get("hooks", [])}
    for hook in ("ruff", "ruff-format", "prettier", "check-json", "check-yaml", "end-of-file-fixer", "reuse"):
        assert any(i and (i == hook or i.startswith(hook)) for i in ids), f"pre-commit lacks {hook}: {sorted(ids)}"


# ---------------------------------------------------------------- M0S-E01-05 devcontainer
@story("M0S-E01-05")
def test_devcontainer_has_python_and_node() -> None:
    dc = jsonc(".devcontainer/devcontainer.json", "M0S-E01-05")
    blob = str(dc).lower()
    assert "3.13" in blob and "python" in blob, "devcontainer must provide Python 3.13"
    assert "node" in blob and "24" in blob, "devcontainer must provide Node 24"
