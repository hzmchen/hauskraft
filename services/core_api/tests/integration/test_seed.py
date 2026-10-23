# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E11-02, M1S-E02-03, M1S-E03-03: `hauskraft seed` creates the demo household once, with demo as owner
and the household settings."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from typer.testing import CliRunner

from hauskraft_core.app import create_app
from hauskraft_core.cli import app as cli
from hauskraft_core.db import migrations
from hauskraft_core.db.models import OutboxEvent, User
from hauskraft_core.settings import Settings

pytestmark = pytest.mark.integration


@pytest.fixture
def empty_db(pg_url: str, db_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Iterator[Settings]:
    admin = create_engine(pg_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS seed_probe WITH (FORCE)"))
        conn.execute(text("CREATE DATABASE seed_probe"))
    url = make_url(pg_url).set(database="seed_probe").render_as_string(hide_password=False)
    settings = db_settings.model_copy(update={"database_url": url, "allowed_origins": ["http://testserver"]})
    migrations.upgrade(settings)
    monkeypatch.setenv("HAUSKRAFT_DATABASE_URL", url)
    monkeypatch.setenv("HAUSKRAFT_PLUGIN_PATHS", ",".join(str(p) for p in settings.plugin_paths))
    monkeypatch.setenv("HAUSKRAFT_THEME_PATHS", "")
    monkeypatch.setenv("HAUSKRAFT_SEED_DEMO", "true")
    yield settings
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS seed_probe WITH (FORCE)"))
    admin.dispose()


def _count(url: str, model: type) -> int:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            return int(conn.execute(select(func.count()).select_from(model)).scalar_one())
    finally:
        engine.dispose()


def test_seed_creates_the_household_once(empty_db: Settings) -> None:
    first = CliRunner().invoke(cli, ["seed", "--if-empty"])
    assert first.exit_code == 0, first.output
    assert _count(empty_db.database_url, User) == 2
    events = _count(empty_db.database_url, OutboxEvent)
    assert events == 7, "2 user.created + 1 settings.household_changed + 3 task.created + 1 task.completed"
    second = CliRunner().invoke(cli, ["seed", "--if-empty"])
    assert second.exit_code == 0, second.output
    assert "already" in second.output
    assert _count(empty_db.database_url, User) == 2
    assert _count(empty_db.database_url, OutboxEvent) == events

    with TestClient(create_app(empty_db), headers={"Origin": "http://testserver"}) as client:
        for username, display, role in (("demo", "Demo Adult", "owner"), ("alex", "Alex Adult", "adult")):
            r = client.post("/api/v1/auth/login", json={"username": username, "password": "hauskraft-demo"})
            assert r.status_code == 200, r.text
            assert r.json()["user"]["display_name"] == display
            assert r.json()["user"]["role"] == role
        titles = {t["title"]: t for t in client.get("/api/v1/tasks").json()["items"]}
    assert set(titles) == {"Water the plants", "Take out recycling", "Book chimney sweep"}
    assert titles["Book chimney sweep"]["done"] is True
    assert titles["Water the plants"]["created_by"]["display_name"] == "Demo Adult"


def test_seed_disabled_by_setting(empty_db: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HAUSKRAFT_SEED_DEMO", "false")
    result = CliRunner().invoke(cli, ["seed", "--if-empty"])
    assert result.exit_code == 0, result.output
    assert "disabled" in result.output
    assert _count(empty_db.database_url, User) == 0


def test_production_refuses_demo_passwords(empty_db: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HAUSKRAFT_ENV", "production")
    monkeypatch.setenv("HAUSKRAFT_SECRET_KEY", "p" * 40)
    refused = CliRunner().invoke(cli, ["seed"])
    assert refused.exit_code == 1
    assert "--force-demo" in refused.output
    assert _count(empty_db.database_url, User) == 0
    forced = CliRunner().invoke(cli, ["seed", "--force-demo"])
    assert forced.exit_code == 0, forced.output
    assert _count(empty_db.database_url, User) == 2


def test_seed_writes_no_theme_setting(empty_db: Settings) -> None:
    assert CliRunner().invoke(cli, ["seed"]).exit_code == 0
    engine = create_engine(empty_db.database_url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM deployment_settings WHERE key = 'theme_id'")).scalar_one() == 0
    engine.dispose()


def test_seed_sets_the_household_settings(empty_db: Settings) -> None:
    assert CliRunner().invoke(cli, ["seed"]).exit_code == 0
    with TestClient(create_app(empty_db), headers={"Origin": "http://testserver"}) as client:
        client.post("/api/v1/auth/login", json={"username": "alex", "password": "hauskraft-demo"})
        assert client.get("/api/v1/household").json() == {
            "name": "Demo household",
            "timezone": "Europe/Berlin",
            "locale": "en",
        }
