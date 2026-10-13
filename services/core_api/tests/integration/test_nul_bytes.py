# SPDX-License-Identifier: AGPL-3.0-or-later
"""PostgreSQL text cannot hold NUL bytes: inputs that reach the database must reject them as 422, not 500.

Found by the Schemathesis fuzz test (``{"title": "\\x00"}`` on ``POST /tasks``).
"""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration


@pytest.fixture
def h(client: TestClient, make_user: Callable[..., str]) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={"username": make_user("Demo Adult"), "password": PASSWORD})
    return {"X-CSRF-Token": r.json()["csrf_token"]}


@pytest.mark.parametrize("title", ["\x00", "Buy\x00milk"])
def test_task_title_with_nul_is_422(client: TestClient, h: dict[str, str], title: str) -> None:
    assert client.post("/api/v1/tasks", json={"title": title}, headers=h).status_code == 422
    task = client.post("/api/v1/tasks", json={"title": "ok"}, headers=h).json()
    assert client.patch(f"/api/v1/tasks/{task['id']}", json={"title": title}, headers=h).status_code == 422


def test_display_name_with_nul_is_422(client: TestClient, h: dict[str, str]) -> None:
    assert client.patch("/api/v1/me", json={"display_name": "A\x00"}, headers=h).status_code == 422
    body = {"username": "kim", "display_name": "Kim\x00", "password": "long enough password"}
    assert client.post("/api/v1/users", json=body, headers=h).status_code == 422


def test_login_with_nul_is_a_client_error(client: TestClient, make_user: Callable[..., str]) -> None:
    username = make_user()
    for body in ({"username": f"{username}\x00", "password": PASSWORD}, {"username": "\x00", "password": "x"}):
        assert client.post("/api/v1/auth/login", json=body).status_code in (401, 422)
