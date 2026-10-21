# SPDX-License-Identifier: MIT
"""Black-box HTTP client for live acceptance tests against a running Hauskraft stack.

Environment:
  HAUSKRAFT_BASE_URL   default http://localhost:8080 (the Caddy web container; /api is proxied)
  HAUSKRAFT_DEMO_PASSWORD  default hauskraft-demo (seeded by M0S-E11-02)
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import httpx
import pytest

BASE_URL = os.environ.get("HAUSKRAFT_BASE_URL", "http://localhost:8080").rstrip("/")
API = f"{BASE_URL}/api/v1"
DEMO_PASSWORD = os.environ.get("HAUSKRAFT_DEMO_PASSWORD", "hauskraft-demo")
PROBLEM_JSON = "application/problem+json"


class Api:
    """An httpx client with cookie jar, Origin header and CSRF token handling."""

    def __init__(self, origin: str | None = None) -> None:
        self.origin = origin or BASE_URL
        self.http = httpx.Client(base_url=API, timeout=15, follow_redirects=False,
                                 headers={"Origin": self.origin})
        self.csrf: str | None = None
        self.session: dict[str, Any] | None = None

    def close(self) -> None:
        self.http.close()

    def login(self, username: str, password: str = DEMO_PASSWORD) -> httpx.Response:
        r = self.http.post("/auth/login", json={"username": username, "password": password})
        if r.status_code == 200:
            self.session = r.json()
            self.csrf = self.session.get("csrf_token")
        return r

    def _headers(self, extra: dict[str, str] | None) -> dict[str, str]:
        h = {}
        if self.csrf:
            h["X-CSRF-Token"] = self.csrf
        if extra:
            h.update(extra)
        return h

    def get(self, path: str, **kw: Any) -> httpx.Response:
        return self.http.get(path, **kw)

    def post(self, path: str, json: Any = None, headers: dict[str, str] | None = None, **kw: Any) -> httpx.Response:
        return self.http.post(path, json=json, headers=self._headers(headers), **kw)

    def patch(self, path: str, json: Any = None, headers: dict[str, str] | None = None, **kw: Any) -> httpx.Response:
        return self.http.patch(path, json=json, headers=self._headers(headers), **kw)

    def put(self, path: str, json: Any = None, headers: dict[str, str] | None = None, **kw: Any) -> httpx.Response:
        return self.http.put(path, json=json, headers=self._headers(headers), **kw)

    def delete(self, path: str, headers: dict[str, str] | None = None, **kw: Any) -> httpx.Response:
        return self.http.delete(path, headers=self._headers(headers), **kw)


def reachable() -> None:
    try:
        httpx.get(f"{API}/healthz", timeout=3)
    except httpx.HTTPError as exc:
        pytest.fail(f"RED: no Hauskraft stack at {BASE_URL} ({exc.__class__.__name__}). "
                    "Start it with `docker compose -f compose.yaml -f deploy/compose/compose.test.yaml up --wait`.",
                    pytrace=False)


@contextmanager
def logged_in(username: str = "demo") -> Iterator[Api]:
    reachable()
    api = Api()
    r = api.login(username)
    if r.status_code != 200:
        api.close()
        pytest.fail(f"RED: cannot log in as {username!r}: {r.status_code} {r.text[:200]}", pytrace=False)
    try:
        yield api
    finally:
        api.close()


def unique(label: str) -> str:
    return f"acc-{uuid.uuid4().hex[:8]} {label}"


def assert_problem(r: httpx.Response, status: int, code: str | None = None) -> dict[str, Any]:
    assert r.status_code == status, f"expected {status}, got {r.status_code}: {r.text[:300]}"
    assert r.headers.get("content-type", "").startswith(PROBLEM_JSON), r.headers.get("content-type")
    body = r.json()
    for field in ("type", "title", "status", "code", "request_id"):
        assert field in body, f"problem+json missing {field!r}: {body}"
    assert body["status"] == status
    if code is not None:
        assert body["code"] == code, body
    return body
