# SPDX-License-Identifier: MIT
"""E11 · Deployment & demo. Static checks on Compose files, Caddy config and how-to-test docs."""

from __future__ import annotations

import pytest

from _support.files import yaml_doc
from _support.red import require_text

story = pytest.mark.story


@story("M0S-E11-01")
def test_root_compose_includes_deploy_stack() -> None:
    doc = yaml_doc("compose.yaml", "M0S-E11-01") or {}
    inc = doc.get("include", [])
    flat = [i if isinstance(i, str) else (i.get("path") if isinstance(i.get("path"), str) else " ".join(i.get("path", []))) for i in inc]
    assert any("deploy/compose/compose.yaml" in (p or "") for p in flat), f"compose.yaml should include the deploy stack: {inc}"


@story("M0S-E11-01")
def test_deploy_stack_services() -> None:
    doc = yaml_doc("deploy/compose/compose.yaml", "M0S-E11-01") or {}
    services = doc.get("services", {})
    for name in ("db", "migrate", "api", "web"):
        assert name in services, f"service {name!r} missing"
    assert str(services["db"].get("image", "")).startswith("postgres:16"), "Postgres 16 is the pinned DB"
    assert "readyz" in str(services["api"].get("healthcheck", "")), "api healthcheck must use /api/v1/readyz"
    assert "8080" in str(services["web"].get("ports", "")), "web must publish 8080"
    deps = services["api"].get("depends_on", {})
    assert "migrate" in deps and (deps["migrate"] or {}).get("condition") == "service_completed_successfully"


@story("M0S-E11-01")
def test_test_overlay_mounts_fixture_themes() -> None:
    text = require_text("deploy/compose/compose.test.yaml", "M0S-E11-01")
    assert "tests/fixtures/themes" in text, "the test overlay must mount tests/fixtures/themes read-only"
    assert ":ro" in text
    assert "HEARTHOS_THEME_PATHS" in text


@story("M0S-E11-01")
def test_env_example_lists_settings() -> None:
    text = require_text("deploy/compose/.env.example", "M0S-E11-01")
    for var in ("HEARTHOS_SECRET_KEY", "HEARTHOS_COOKIE_SECURE", "HEARTHOS_ALLOWED_ORIGINS",
                "HEARTHOS_DEFAULT_THEME", "HEARTHOS_WEB_PORT"):
        assert var in text, f".env.example lacks {var}"


@story("M0S-E11-01")
def test_caddy_sets_strict_csp() -> None:
    text = require_text("deploy/compose/Caddyfile", "M0S-E11-01")
    assert "Content-Security-Policy" in text
    for directive in ("default-src 'self'", "frame-ancestors 'none'", "font-src 'self'"):
        assert directive in text, f"CSP lacks {directive}"


@story("M0S-E11-03")
def test_how_to_test_doc() -> None:
    text = require_text("docs/how-to-test.md", "M0S-E11-03")
    for needle in ("docker compose up --wait", "docker compose down -v", "HEARTHOS_WEB_PORT",
                   "themes validate", "data/themes", "pytest tests", "--live"):
        assert needle in text, f"how-to-test.md should mention {needle!r}"
