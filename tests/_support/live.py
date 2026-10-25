# SPDX-License-Identifier: MIT
"""Black-box HTTP client for live acceptance tests against a running Hauskraft stack.

Environment:
  HAUSKRAFT_BASE_URL   default http://localhost:8080 (the Caddy web container; /api is proxied)
  HAUSKRAFT_DEMO_PASSWORD  default hauskraft-demo (seeded by M0S-E11-02)
  HAUSKRAFT_FRESH_BASE_URL  the unseeded stack for first-run tests (M1S-E01-01), e.g. http://localhost:8081
  HAUSKRAFT_FRESH_RESET_CMD  shell command that leaves an empty, healthy fresh stack (M1S-E01-01)
  HAUSKRAFT_FAKE_LLM_URL  the fake model's base URL as the API container sees it (M2S-E01-01), default
                          http://fake-llm:8090/v1
  HAUSKRAFT_FAKE_LLM_ADMIN_URL  the fake model as the tests see it (recorded requests), default http://localhost:8090
"""

from __future__ import annotations

import os
import subprocess
import time
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
FRESH_BASE_URL = os.environ.get("HAUSKRAFT_FRESH_BASE_URL", "http://localhost:8081").rstrip("/")
FRESH_RESET_CMD = os.environ.get("HAUSKRAFT_FRESH_RESET_CMD", "")
FAKE_LLM_URL = os.environ.get("HAUSKRAFT_FAKE_LLM_URL", "http://fake-llm:8090/v1").rstrip("/")
FAKE_LLM_ADMIN_URL = os.environ.get("HAUSKRAFT_FAKE_LLM_ADMIN_URL", "http://localhost:8090").rstrip("/")
FAKE_KEY = "sk-hauskraft-fake-key-abcd"  # a test key for the fake model; its hint is "abcd"
# Passwords used for throwaway accounts (M1*): all meet the 12-character policy.
TEMP_PASSWORD = "temporary-pass-1234"
MEMBER_PASSWORD = "member-chosen-pass-5678"


class Api:
    """An httpx client with cookie jar, Origin header and CSRF token handling."""

    def __init__(self, origin: str | None = None, base_url: str | None = None) -> None:
        self.base_url = (base_url or BASE_URL).rstrip("/")
        self.origin = origin or self.base_url
        self.http = httpx.Client(base_url=f"{self.base_url}/api/v1", timeout=15, follow_redirects=False,
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


def reachable(base_url: str = BASE_URL) -> None:
    try:
        httpx.get(f"{base_url}/api/v1/healthz", timeout=3)
    except httpx.HTTPError as exc:
        hint = ("`just fresh-up` (M1S-E01-01)" if base_url == FRESH_BASE_URL else
                "`docker compose -f compose.yaml -f deploy/compose/compose.test.yaml up --wait`")
        pytest.fail(f"RED: no Hauskraft stack at {base_url} ({exc.__class__.__name__}). Start it with {hint}.",
                    pytrace=False)


@contextmanager
def logged_in(username: str = "demo", password: str = DEMO_PASSWORD, base_url: str | None = None) -> Iterator[Api]:
    reachable(base_url or BASE_URL)
    api = Api(base_url=base_url)
    r = api.login(username, password)
    if r.status_code != 200:
        api.close()
        pytest.fail(f"RED: cannot log in as {username!r}: {r.status_code} {r.text[:200]}", pytrace=False)
    try:
        yield api
    finally:
        api.close()


def sign_in(username: str, password: str, base_url: str | None = None) -> Api:
    """A separate browser-like client; the caller closes it."""
    api = Api(base_url=base_url)
    r = api.login(username, password)
    assert r.status_code == 200, r.text
    return api


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


def wait_for_activity(api: Api, subject: str, event_type: str, timeout: float = 15) -> dict[str, Any] | None:
    """Poll the activity feed for an entry about ``subject`` of ``event_type`` (the outbox relay is asynchronous)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        items = api.get("/activity", params={"limit": 100}).json()
        hit = next((i for i in items if i.get("subject") == subject and i.get("type") == event_type), None)
        if hit:
            return hit
        time.sleep(0.5)
    return None


def activity_types_for(api: Api, subject: str) -> list[str]:
    """Event types about ``subject`` currently in the feed, newest first."""
    return [i["type"] for i in api.get("/activity", params={"limit": 100}).json() if i.get("subject") == subject]


def fresh_setup_required() -> bool:
    reachable(FRESH_BASE_URL)
    r = httpx.get(f"{FRESH_BASE_URL}/api/v1/setup", timeout=5)
    if r.status_code != 200:
        pytest.fail(f"RED (M1S-E03-01): GET /setup on the fresh stack answered {r.status_code}", pytrace=False)
    return bool(r.json().get("required"))


def reset_fresh_stack() -> None:
    """Leave the fresh stack empty: run HAUSKRAFT_FRESH_RESET_CMD if setup was already done."""
    if fresh_setup_required():
        return
    if not FRESH_RESET_CMD:
        pytest.fail("the fresh stack is already set up and HAUSKRAFT_FRESH_RESET_CMD is not set; run `just fresh-reset`",
                    pytrace=False)
    subprocess.run(FRESH_RESET_CMD, shell=True, check=True, timeout=600)  # noqa: S602 - test-only, from the env
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            if fresh_setup_required():
                return
        except (httpx.HTTPError, pytest.fail.Exception):  # still restarting
            pass
        time.sleep(2)
    pytest.fail("the fresh stack did not come back empty after HAUSKRAFT_FRESH_RESET_CMD", pytrace=False)


# ---------------------------------------------------------------- M2*: the fake model (tests/fixtures/fake-llm/)
def fake_requests(contains: str = "", limit: int = 100) -> list[dict[str, Any]]:
    """Requests the fake model received whose messages contain ``contains``, oldest first."""
    try:
        r = httpx.get(f"{FAKE_LLM_ADMIN_URL}/_requests", params={"contains": contains, "limit": limit}, timeout=5)
    except httpx.HTTPError as exc:
        pytest.fail(f"RED (M2S-E01-01): no fake model at {FAKE_LLM_ADMIN_URL} ({exc.__class__.__name__}); start the "
                    "test stack with the fake-llm service", pytrace=False)
    assert r.status_code == 200, r.text
    return r.json()


def system_prompt(record: dict[str, Any]) -> str:
    """The system message text of a recorded request."""
    parts = []
    for m in record["messages"]:
        if m.get("role") in ("system", "developer"):
            c = m.get("content")
            parts.append(c if isinstance(c, str) else "\n".join(p.get("text", "") for p in c or []))
    return "\n".join(parts)


def configure_fake(owner: Api, model: str = "fake-tools", api_key: str = FAKE_KEY, **chat: Any) -> dict[str, Any]:
    """Point the assistant at the fake model (owner only) and return the settings."""
    body = {"chat": {"base_url": FAKE_LLM_URL, "model": model, "api_key": api_key, **chat}}
    r = owner.patch("/assistant/settings", json=body)
    if r.status_code != 200:
        pytest.fail(f"RED (M2S-E03-02): PATCH /assistant/settings answered {r.status_code}: {r.text[:200]}",
                    pytrace=False)
    return r.json()


def new_chat(api: Api) -> str:
    r = api.post("/assistant/conversations")
    if r.status_code != 201:
        pytest.fail(f"RED (M2S-E04-01): POST /assistant/conversations answered {r.status_code}: {r.text[:200]}",
                    pytrace=False)
    return r.json()["id"]


def say(api: Api, conversation_id: str, text: str) -> dict[str, Any]:
    """Send a chat message and return the RunResult (fails the test on a non-200 answer)."""
    r = api.post(f"/assistant/conversations/{conversation_id}/messages", json={"text": text}, timeout=90)
    assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
    return r.json()


def tasks_titled(api: Api, title: str) -> list[dict[str, Any]]:
    items = api.get("/tasks", params={"status": "all", "limit": 100}).json()["items"]
    return [t for t in items if t["title"] == title]

