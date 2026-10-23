# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E05-05, M1S-E02-02: owners create owner and adult accounts through the API; the `hauskraft` CLI."""

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from hauskraft_core.app import create_app
from hauskraft_core.cli import app as cli
from hauskraft_core.settings import Settings
from tests.integration.conftest import PASSWORD

pytestmark = pytest.mark.integration


def _login(client: TestClient, username: str, password: str = PASSWORD):  # type: ignore[no-untyped-def]
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _signed_in(client: TestClient, make_user: Callable[..., str], role: str = "owner") -> dict[str, str]:
    return {"X-CSRF-Token": _login(client, make_user(role=role)).json()["csrf_token"]}


@pytest.mark.parametrize(("body", "role"), [({}, "adult"), ({"role": "adult"}, "adult"), ({"role": "owner"}, "owner")])
def test_owner_creates_owner_or_adult(
    client: TestClient, make_user: Callable[..., str], api_settings: Settings, body: dict[str, str], role: str
) -> None:
    headers = _signed_in(client, make_user)
    username = "anna" + uuid.uuid4().hex[:6]
    r = client.post(
        "/api/v1/users",
        json={"username": username, "display_name": "Anna", "password": "correct-horse-battery", **body},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["role"] == role
    assert r.json()["username"] == username
    with TestClient(create_app(api_settings), headers={"Origin": "http://testserver"}) as other:
        assert _login(other, username, "correct-horse-battery").status_code == 200


def test_adults_cannot_create_accounts(client: TestClient, make_user: Callable[..., str]) -> None:
    headers = _signed_in(client, make_user, role="adult")
    r = client.post(
        "/api/v1/users",
        json={"username": "denied" + uuid.uuid4().hex[:6], "display_name": "D", "password": "correct-horse-battery"},
        headers=headers,
    )
    assert r.status_code == 403
    assert r.json()["code"] == "policy_denied"


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({"password": "short"}, 422, None),
        ({"password": "x" * 129}, 422, None),
        ({"role": "kid"}, 422, "role_not_enabled"),
        ({"role": "superuser"}, 422, None),
        ({"username": "Has Space"}, 422, "invalid_username"),
    ],
)
def test_validation(
    client: TestClient, make_user: Callable[..., str], body: dict[str, str], status: int, code: str | None
) -> None:
    headers = _signed_in(client, make_user)
    payload = {"username": "v" + uuid.uuid4().hex[:8], "display_name": "V", "password": "correct-horse-battery", **body}
    r = client.post("/api/v1/users", json=payload, headers=headers)
    assert r.status_code == status, r.text
    if code:
        assert r.json()["code"] == code


def test_duplicate_username(client: TestClient, make_user: Callable[..., str]) -> None:
    headers = _signed_in(client, make_user)
    existing = make_user()
    r = client.post(
        "/api/v1/users",
        json={"username": existing, "display_name": "X", "password": "correct-horse-battery"},
        headers=headers,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "username_taken"


def test_creating_users_needs_a_session(client: TestClient) -> None:
    r = client.post(
        "/api/v1/users", json={"username": "nobody", "display_name": "N", "password": "correct-horse-battery"}
    )
    assert r.status_code == 401


def test_cli_create_prompts_for_the_password(
    api_settings: Settings, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.setenv("HAUSKRAFT_DATABASE_URL", api_settings.database_url)
    username = "cli" + uuid.uuid4().hex[:6]
    result = CliRunner().invoke(
        cli,
        ["users", "create", "--username", username, "--display-name", "Cli Adult"],
        input="correct-horse-battery\ncorrect-horse-battery\n",
    )
    assert result.exit_code == 0, result.output
    assert username in result.output
    assert _login(client, username, "correct-horse-battery").status_code == 200

    changed = CliRunner().invoke(
        cli, ["users", "set-password", "--username", username], input="another-long-password\nanother-long-password\n"
    )
    assert changed.exit_code == 0, changed.output
    assert _login(client, username, "another-long-password").status_code == 200


def test_cli_reports_errors_without_a_traceback(api_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HAUSKRAFT_DATABASE_URL", api_settings.database_url)
    result = CliRunner().invoke(cli, ["users", "create", "--username", "x y"], input="short\nshort\n")
    assert result.exit_code == 1
    assert "Traceback" not in result.output


def test_cli_db_upgrade_is_idempotent(api_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HAUSKRAFT_DATABASE_URL", api_settings.database_url)
    monkeypatch.setenv("HAUSKRAFT_PLUGIN_PATHS", ",".join(str(p) for p in api_settings.plugin_paths))
    result = CliRunner().invoke(cli, ["db", "upgrade"])
    assert result.exit_code == 0, result.output
