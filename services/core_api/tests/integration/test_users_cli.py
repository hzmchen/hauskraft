# SPDX-License-Identifier: AGPL-3.0-or-later
"""M1S-E06-06: the `hauskraft users` CLI can do what owners do in the app, for recovery without a working owner."""

import json
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from typer.testing import CliRunner

from hauskraft_core.cli import app as cli
from hauskraft_core.db import migrations
from hauskraft_core.db.models import OutboxEvent, User
from hauskraft_core.settings import Settings

pytestmark = pytest.mark.integration

PASSWORD = "cli-chosen-password-1"
TWICE = f"{PASSWORD}\n{PASSWORD}\n"


@pytest.fixture
def household(pg_url: str, db_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Iterator[Settings]:
    """An empty, migrated database the CLI points at."""
    admin = create_engine(pg_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS cli_probe WITH (FORCE)"))
        conn.execute(text("CREATE DATABASE cli_probe"))
    url = make_url(pg_url).set(database="cli_probe").render_as_string(hide_password=False)
    settings = db_settings.model_copy(update={"database_url": url})
    migrations.upgrade(settings)
    monkeypatch.setenv("HAUSKRAFT_DATABASE_URL", url)
    yield settings
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS cli_probe WITH (FORCE)"))
    admin.dispose()


def _cli(*args: str, password: bool = False) -> Any:
    return CliRunner().invoke(cli, ["users", *args], input=TWICE if password else None)


def _user(settings: Settings, username: str) -> Any:
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as conn:
            return conn.execute(select(User).where(User.username == username)).one()
    finally:
        engine.dispose()


def _event_types(settings: Settings, username: str) -> list[str]:
    user_id = _user(settings, username).id
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                select(OutboxEvent.type).where(OutboxEvent.subject == f"user/{user_id}").order_by(OutboxEvent.time)
            )
            return [row[0] for row in rows]
    finally:
        engine.dispose()


def test_create_owner_or_temporary_adult(household: Settings) -> None:
    r = _cli("create", "--username", "mia", "--display-name", "Mia", "--role", "owner", password=True)
    assert r.exit_code == 0, r.output
    assert "owner" in r.output
    mia = _user(household, "mia")
    assert (str(mia.role), mia.must_change_password) == ("owner", False)
    r = _cli("create", "--username", "alex", "--temporary", password=True)
    assert r.exit_code == 0, r.output
    alex = _user(household, "alex")
    assert (str(alex.role), alex.must_change_password) == ("adult", True)
    assert _event_types(household, "alex") == ["hauskraft.user.created"]
    assert _cli("create", "--username", "kid", "--role", "kid", password=True).exit_code == 1


def test_list_shows_role_and_status_and_json_lists_members(household: Settings) -> None:
    _cli("create", "--username", "mia", "--display-name", "Mia", "--role", "owner", password=True)
    _cli("create", "--username", "alex", "--display-name", "Alex", password=True)
    assert _cli("deactivate", "alex").exit_code == 0
    text_out = _cli("list")
    assert text_out.exit_code == 0, text_out.output
    lines = {line.split()[0]: line for line in text_out.output.splitlines() if line.strip()}
    assert "owner" in lines["mia"]
    assert "active" in lines["mia"]
    assert "adult" in lines["alex"]
    assert "deactivated" in lines["alex"]
    as_json = _cli("list", "--json")
    members = {m["username"]: m for m in json.loads(as_json.output)}
    assert set(members) == {"mia", "alex"}
    assert members["alex"]["is_active"] is False
    assert "password_hash" not in as_json.output


def test_set_password_by_username_with_and_without_temporary(household: Settings) -> None:
    _cli("create", "--username", "mia", "--role", "owner", password=True)
    r = CliRunner().invoke(cli, ["users", "set-password", "mia", "--temporary"], input=TWICE)
    assert r.exit_code == 0, r.output
    assert _user(household, "mia").must_change_password is True
    r = CliRunner().invoke(cli, ["users", "set-password", "--username", "mia"], input=TWICE)
    assert r.exit_code == 0, r.output
    assert _user(household, "mia").must_change_password is False
    assert _event_types(household, "mia") == [
        "hauskraft.user.created",
        "hauskraft.user.password_reset",
        "hauskraft.user.password_reset",
    ]


def test_deactivate_and_reactivate_keep_the_last_owner_rule(household: Settings) -> None:
    _cli("create", "--username", "mia", "--role", "owner", password=True)
    _cli("create", "--username", "alex", password=True)
    last = _cli("deactivate", "mia")
    assert last.exit_code == 1
    assert "owner" in last.output
    assert _user(household, "mia").is_active is True
    assert _cli("deactivate", "alex").exit_code == 0
    assert _cli("reactivate", "alex").exit_code == 0
    assert _user(household, "alex").is_active is True
    assert _event_types(household, "alex")[1:] == ["hauskraft.user.deactivated", "hauskraft.user.reactivated"]
    unknown = _cli("deactivate", "nobody" + uuid.uuid4().hex[:4])
    assert unknown.exit_code == 1
    assert "Traceback" not in unknown.output
