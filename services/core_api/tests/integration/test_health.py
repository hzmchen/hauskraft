# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E03-02: liveness never touches the database; readiness reports named checks."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from hearthos_core.app import create_app
from hearthos_core.db import migrations
from hearthos_core.health import register_check
from hearthos_core.settings import Settings
from tests.theme_helpers import builtin_default

pytestmark = pytest.mark.integration


@pytest.fixture
def fresh_db(pg_url: str) -> Iterator[str]:
    """A brand-new, unmigrated database next to the shared one."""
    admin = create_engine(pg_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS readyz_probe"))
        conn.execute(text("CREATE DATABASE readyz_probe"))
    yield make_url(pg_url).set(database="readyz_probe").render_as_string(hide_password=False)
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS readyz_probe WITH (FORCE)"))
    admin.dispose()


def _settings(url: str, theme_paths: list[Path] | None = None) -> Settings:
    return Settings(env="test", database_url=url, plugin_paths=[], theme_paths=theme_paths or [], relay_enabled=False)


def test_healthz_needs_no_database() -> None:
    app = create_app(_settings("postgresql+psycopg://x:y@127.0.0.1:9/nowhere"))
    with TestClient(app) as client:
        r = client.get("/api/v1/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_readyz_fails_without_database() -> None:
    app = create_app(_settings("postgresql+psycopg://x:y@127.0.0.1:9/nowhere"))
    with TestClient(app) as client:
        r = client.get("/api/v1/readyz")
    assert r.status_code == 503
    checks = {c["name"]: c for c in r.json()["checks"]}
    assert checks["database"]["ok"] is False
    assert checks["database"]["detail"]


def test_readyz_503_before_migration_and_200_after(fresh_db: str, tmp_path: Path) -> None:
    settings = _settings(fresh_db, [builtin_default(tmp_path)])
    with TestClient(create_app(settings)) as client:
        before = client.get("/api/v1/readyz")
        assert before.status_code == 503
        checks = {c["name"]: c for c in before.json()["checks"]}
        assert checks["database"]["ok"] is True
        assert checks["migrations"]["ok"] is False

        migrations.upgrade(settings)
        after = client.get("/api/v1/readyz")
        assert after.status_code == 200, after.text
        body = after.json()
        assert body["status"] == "ready"
        assert {"database", "migrations", "plugins", "theme"} <= {c["name"] for c in body["checks"]}
        assert all({"name", "ok", "detail"} <= set(c) for c in body["checks"])


def test_registered_checks_take_part(db_settings: Settings) -> None:
    app = create_app(_settings(db_settings.database_url))

    async def broken() -> tuple[bool, str]:
        return False, "default theme failed to compile"

    register_check(app, "theme", broken)
    with TestClient(app) as client:
        r = client.get("/api/v1/readyz")
    assert r.status_code == 503
    assert {"name": "theme", "ok": False, "detail": "default theme failed to compile"} in r.json()["checks"]


def test_failed_plugins_make_readiness_fail(db_settings: Settings) -> None:
    app = create_app(_settings(db_settings.database_url))
    with TestClient(app) as client:
        app.state.plugin_load_errors["org.example.broken"] = "ImportError: no module named broken"
        r = client.get("/api/v1/readyz")
    assert r.status_code == 503
    plugins = next(c for c in r.json()["checks"] if c["name"] == "plugins")
    assert plugins["ok"] is False
    assert "org.example.broken" in plugins["detail"]
