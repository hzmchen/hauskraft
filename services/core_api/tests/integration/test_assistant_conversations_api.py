# SPDX-License-Identifier: AGPL-3.0-or-later
"""M2S-E04-01: conversations are private to their writer, owners included, and kept until deleted."""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from hauskraft_core.app import create_app
from hauskraft_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration
BASE = "/api/v1/assistant/conversations"


@pytest.fixture
def signed_in(api_settings: Settings, make_user: Callable[..., str]) -> Iterator[Callable[[str], TestClient]]:
    opened: list[TestClient] = []

    def _open(role: str) -> TestClient:
        c = TestClient(create_app(api_settings), headers={"Origin": "http://testserver"})
        c.__enter__()
        opened.append(c)
        r = c.post("/api/v1/auth/login", json={"username": make_user(role=role), "password": PASSWORD})
        c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
        return c

    yield _open
    for c in opened:
        c.__exit__(None, None, None)


def test_create_list_read_delete(signed_in: Callable[[str], TestClient]) -> None:
    me = signed_in("adult")
    first = me.post(BASE)
    assert first.status_code == 201, first.text
    second = me.post(BASE).json()
    assert first.json()["title"] is None
    assert [c["id"] for c in me.get(BASE).json()] == [second["id"], first.json()["id"]]
    detail = me.get(f"{BASE}/{second['id']}").json()
    assert detail["messages"] == []
    assert detail["actions"] == []
    assert me.delete(f"{BASE}/{second['id']}").status_code == 204
    assert me.get(f"{BASE}/{second['id']}").status_code == 404
    assert [c["id"] for c in me.get(BASE).json()] == [first.json()["id"]]


def test_private_even_from_owners(signed_in: Callable[[str], TestClient]) -> None:
    adult, owner = signed_in("adult"), signed_in("owner")
    mine = adult.post(BASE).json()["id"]
    assert owner.get(BASE).json() == []
    for method in ("get", "delete"):
        r = getattr(owner, method)(f"{BASE}/{mine}")
        assert r.status_code == 404
        assert r.json()["code"] == "not_found"
    assert adult.get(f"{BASE}/{mine}").status_code == 200


def test_unknown_or_malformed_ids_are_404(signed_in: Callable[[str], TestClient]) -> None:
    me = signed_in("adult")
    assert me.get(f"{BASE}/0199f390-1111-7aaa-8bbb-000000000099").status_code == 404
    assert me.get(f"{BASE}/not-a-uuid").status_code in (404, 422)


def test_needs_a_session(api_settings: Settings) -> None:
    with TestClient(create_app(api_settings), headers={"Origin": "http://testserver"}) as anon:
        assert anon.get(BASE).status_code == 401
