# SPDX-License-Identifier: AGPL-3.0-or-later
"""M1S-E07-01: accounts an owner creates must replace the temporary password before anything else."""

import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from hauskraft_core.app import create_app
from hauskraft_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration

TEMPORARY = "temporary-pass-1234"
CHOSEN = "member-chosen-pass-5678"


@pytest.fixture
def browser(api_settings: Settings) -> Iterator[Callable[[str, str], TestClient]]:
    opened: list[TestClient] = []

    def _open(username: str, password: str) -> TestClient:
        c = TestClient(create_app(api_settings), headers={"Origin": "http://testserver"})
        c.__enter__()
        opened.append(c)
        r = c.post("/api/v1/auth/login", json={"username": username, "password": password})
        assert r.status_code == 200, r.text
        c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
        return c

    yield _open
    for c in opened:
        c.__exit__(None, None, None)


@pytest.fixture
def new_member(browser: Callable[[str, str], TestClient], make_user: Callable[..., str]) -> dict[str, str]:
    owner = browser(make_user(role="owner"), PASSWORD)
    username = "m" + uuid.uuid4().hex[:8]
    r = owner.post("/api/v1/users", json={"username": username, "display_name": "Member", "password": TEMPORARY})
    assert r.status_code == 201, r.text
    assert r.json()["must_change_password"] is True
    return {"username": username, "id": r.json()["id"]}


def test_a_new_account_can_only_change_its_password(
    browser: Callable[[str, str], TestClient], new_member: dict[str, str]
) -> None:
    member = browser(new_member["username"], TEMPORARY)
    assert member.get("/api/v1/auth/session").json()["user"]["must_change_password"] is True
    for method, path in [("GET", "/api/v1/tasks"), ("GET", "/api/v1/activity"), ("PATCH", "/api/v1/me")]:
        r = member.request(method, path, json={} if method == "PATCH" else None)
        assert r.status_code == 403, (method, path, r.text)
        assert r.json()["code"] == "password_change_required"
    for path in ("/api/v1/me", "/api/v1/household", "/api/v1/auth/session"):
        assert member.get(path).status_code == 200, path

    r = member.post("/api/v1/me/password", json={"current_password": TEMPORARY, "new_password": CHOSEN})
    assert r.status_code == 204, r.text
    assert member.get("/api/v1/me").json()["must_change_password"] is False
    assert member.get("/api/v1/tasks").status_code == 200, "unlocked in the same session"


def test_sign_out_works_while_locked(browser: Callable[[str, str], TestClient], new_member: dict[str, str]) -> None:
    member = browser(new_member["username"], TEMPORARY)
    assert member.post("/api/v1/auth/logout").status_code == 204


def test_accounts_not_made_by_an_owner_are_not_locked(
    browser: Callable[[str, str], TestClient], make_user: Callable[..., str]
) -> None:
    """The CLI and the seed create accounts through create_user without temporary=True."""
    me = browser(make_user(), PASSWORD)
    assert me.get("/api/v1/me").json()["must_change_password"] is False
    assert me.get("/api/v1/tasks").status_code == 200
