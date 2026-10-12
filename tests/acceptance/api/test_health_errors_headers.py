# SPDX-License-Identifier: MIT
"""E03-02 health/readiness, E03-03 problem+json and request IDs, E11-01 security headers."""

from __future__ import annotations

import httpx
import pytest

from _support.live import API, BASE_URL, assert_problem, reachable

pytestmark = pytest.mark.live
story = pytest.mark.story


@story("M0S-E03-02")
def test_healthz() -> None:
    reachable()
    r = httpx.get(f"{API}/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


@story("M0S-E03-02")
def test_readyz_lists_checks() -> None:
    reachable()
    r = httpx.get(f"{API}/readyz")
    assert r.status_code == 200, r.text
    body = r.json()
    names = {c.get("name") for c in body.get("checks", [])}
    assert {"database", "migrations", "plugins", "theme"} <= names, body


@story("M0S-E03-03")
def test_unknown_route_is_problem_json() -> None:
    reachable()
    r = httpx.get(f"{API}/does-not-exist", headers={"X-Request-ID": "acc-req-123"})
    body = assert_problem(r, 404)
    assert r.headers.get("x-request-id") == "acc-req-123"
    assert body["request_id"] == "acc-req-123"


@story("M0S-E03-03")
def test_request_id_is_generated_when_absent() -> None:
    reachable()
    r = httpx.get(f"{API}/healthz")
    assert r.headers.get("x-request-id"), "every response should carry X-Request-ID"


@story("M0S-E03-03", "M0S-E07-03")
def test_validation_error_is_problem_json(demo) -> None:
    r = demo.post("/tasks", json={"title": ""})
    body = assert_problem(r, 422)
    assert isinstance(body.get("errors"), list) and body["errors"], body


@story("M0S-E11-01")
def test_web_sets_strict_csp() -> None:
    reachable()
    r = httpx.get(f"{BASE_URL}/")
    assert r.status_code == 200
    csp = r.headers.get("content-security-policy", "")
    for directive in ("default-src 'self'", "frame-ancestors 'none'", "font-src 'self'"):
        assert directive in csp, f"CSP lacks {directive}: {csp}"
    assert "http:" not in csp and "https:" not in csp, f"CSP must not allow external origins: {csp}"


@story("M0S-E11-01")
def test_spa_routes_fall_back_to_index() -> None:
    reachable()
    r = httpx.get(f"{BASE_URL}/today")
    assert r.status_code == 200 and "<html" in r.text.lower()
