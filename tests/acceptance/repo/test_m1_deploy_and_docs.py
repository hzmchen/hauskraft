# SPDX-License-Identifier: MIT
"""M1* static checks: the fresh stack (E01), localhost binding (E03-04) and the household admin docs (E10-01)."""

from __future__ import annotations

import re
from typing import Any

import pytest
import yaml

from _support.red import require_text

story = pytest.mark.story


class _ComposeLoader(yaml.SafeLoader):
    """Compose files may use `!reset` / `!override`; keep the tagged value and drop the tag."""


def _tagged(loader: yaml.SafeLoader, _suffix: str, node: yaml.Node) -> Any:
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return loader.construct_scalar(node)


_ComposeLoader.add_multi_constructor("!", _tagged)


def _compose(rel: str, sid: str) -> dict:
    return yaml.load(require_text(rel, sid), Loader=_ComposeLoader) or {}  # noqa: S506 - safe subclass


def _env(service: dict) -> dict[str, str]:
    env = service.get("environment", {}) or {}
    if isinstance(env, list):
        env = dict(item.split("=", 1) for item in env if "=" in item)
    return {k: str(v) for k, v in env.items()}


# ---------------------------------------------------------------- M1S-E01-01 fresh stack
@story("M1S-E01-01")
def test_fresh_overlay_turns_off_the_demo_seed_and_moves_ports() -> None:
    doc = _compose("deploy/compose/compose.fresh.yaml", "M1S-E01-01")
    services = doc.get("services", {})
    for name in ("migrate", "api"):
        assert _env(services.get(name, {})).get("HAUSKRAFT_SEED_DEMO", "").lower() == "false", name
    assert "8081" in str(services.get("web", {}).get("ports", "")), "the fresh stack serves on 8081"
    assert "http://localhost:8081" in _env(services.get("api", {})).get("HAUSKRAFT_ALLOWED_ORIGINS", "")
    assert "5432" not in str(services.get("db", {}).get("ports", "")), "no database port on the fresh stack"
    assert "ports" in services.get("db", {}), "the overlay must reset the db service's published port"


@story("M1S-E01-01")
def test_justfile_has_fresh_recipes() -> None:
    text = require_text("justfile", "M1S-E01-01")
    for recipe in ("fresh-up", "fresh-reset"):
        m = re.search(rf"^{recipe}\b.*?:\n((?:[ \t]+.*\n?)+)", text, re.M)
        assert m, f"justfile recipe {recipe!r} missing"
        assert "compose.fresh.yaml" in m.group(1) and "hauskraft-fresh" in m.group(1), recipe
    reset = re.search(r"^fresh-reset\b.*?:\n((?:[ \t]+.*\n?)+)", text, re.M)
    assert reset and re.search(r"down\b.*(-v|--volumes)", reset.group(1)), "fresh-reset removes the volumes"


@story("M1S-E01-01")
def test_testing_guide_explains_the_fresh_stack() -> None:
    text = require_text("docs/testing/README.md", "M1S-E01-01")
    for needle in ("HAUSKRAFT_FRESH_BASE_URL", "HAUSKRAFT_FRESH_RESET_CMD", "just fresh-up"):
        assert needle in text, needle


# ---------------------------------------------------------------- M1S-E01-02 CI
@story("M1S-E01-02")
def test_e2e_workflow_runs_the_fresh_stack() -> None:
    text = require_text(".github/workflows/e2e.yml", "M1S-E01-02")
    assert "compose.fresh.yaml" in text and "hauskraft-fresh" in text
    assert "HAUSKRAFT_FRESH_BASE_URL" in text and "HAUSKRAFT_FRESH_RESET_CMD" in text
    assert re.search(r"hauskraft-fresh[^\n]*logs|logs[^\n]*hauskraft-fresh", text), "upload fresh-stack logs on failure"


# ---------------------------------------------------------------- M1S-E03-04 localhost binding
@story("M1S-E03-04")
def test_web_port_binds_to_localhost_by_default() -> None:
    doc = _compose("deploy/compose/compose.yaml", "M1S-E03-04")
    ports = " ".join(str(p) for p in doc["services"]["web"].get("ports", []))
    assert "${HAUSKRAFT_WEB_BIND:-127.0.0.1}:" in ports, ports
    assert "8080" in ports


@story("M1S-E03-04")
def test_env_example_documents_the_bind_address() -> None:
    text = require_text("deploy/compose/.env.example", "M1S-E03-04")
    assert "HAUSKRAFT_WEB_BIND" in text and "TLS" in text


# ---------------------------------------------------------------- M1S-E10-01 docs
@story("M1S-E10-01")
def test_readme_has_both_quick_starts() -> None:
    text = require_text("README.md", "M1S-E10-01")
    assert "HAUSKRAFT_SEED_DEMO=false" in text
    assert re.search(r"set up your household", text, re.I)
    assert "docs/household-admin.md" in text


@story("M1S-E10-01")
def test_household_admin_guide() -> None:
    text = require_text("docs/household-admin.md", "M1S-E10-01")
    for needle in ("hauskraft users set-password", "hauskraft users list", "HAUSKRAFT_WEB_BIND", "TLS"):
        assert needle in text, needle
    for word in ("owner", "adult", "temporary password", "deactivat", "time zone", "first"):
        assert word in text.lower(), word


@story("M1S-E10-01")
def test_how_to_test_covers_m1() -> None:
    text = require_text("docs/how-to-test.md", "M1S-E10-01")
    assert "basics.spec.ts" in text and "fresh-up" in text
