# SPDX-License-Identifier: AGPL-3.0-or-later
"""M1S-E02-03: upgrading from M0* leaves the household with an owner (spec §2.3, ADR 0016)."""

import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from hauskraft_core.db import migrations
from hauskraft_core.settings import Settings

pytestmark = pytest.mark.integration

BEFORE = "0003_outbox_events"
T0 = dt.datetime(2026, 10, 1, 12, 0, tzinfo=dt.UTC)


@pytest.fixture
def m0_db(pg_url: str) -> Iterator[Settings]:
    """A fresh database at the last M0* core revision."""
    admin = create_engine(pg_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS owner_probe WITH (FORCE)"))
        conn.execute(text("CREATE DATABASE owner_probe"))
    url = make_url(pg_url).set(database="owner_probe").render_as_string(hide_password=False)
    settings = Settings(env="test", database_url=url, plugin_paths=[], theme_paths=[])
    migrations.upgrade(settings, BEFORE)
    yield settings
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS owner_probe WITH (FORCE)"))
    admin.dispose()


def _add(settings: Settings, username: str, *, minutes: int, role: str = "adult", active: bool = True) -> uuid.UUID:
    user_id, at = uuid.uuid4(), T0 + dt.timedelta(minutes=minutes)
    engine = create_engine(settings.database_url)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, username, display_name, password_hash, role, is_active, created_at)"
                    " VALUES (:id, :u, :u, 'x', CAST(:role AS user_role), :active, :at)"
                ),
                {"id": user_id, "u": username, "role": role, "active": active, "at": at},
            )
    finally:
        engine.dispose()
    return user_id


def _roles(settings: Settings) -> dict[str, str]:
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as conn:
            return {u: str(r) for u, r in conn.execute(text("SELECT username, role FROM users"))}
    finally:
        engine.dispose()


def test_the_oldest_active_account_becomes_owner(m0_db: Settings) -> None:
    _add(m0_db, "gone", minutes=0, active=False)
    _add(m0_db, "first", minutes=1)
    _add(m0_db, "second", minutes=2)
    migrations.upgrade(m0_db)
    assert _roles(m0_db) == {"gone": "adult", "first": "owner", "second": "adult"}


def test_ties_on_created_at_go_to_the_smaller_id(m0_db: Settings) -> None:
    ids = {name: _add(m0_db, name, minutes=1) for name in ("a1", "a2")}
    migrations.upgrade(m0_db)
    winner = min(ids, key=lambda name: ids[name])
    assert _roles(m0_db) == {name: "owner" if name == winner else "adult" for name in ids}


def test_a_household_with_an_owner_is_left_alone(m0_db: Settings) -> None:
    _add(m0_db, "first", minutes=1)
    _add(m0_db, "boss", minutes=2, role="owner")
    migrations.upgrade(m0_db)
    assert _roles(m0_db) == {"first": "adult", "boss": "owner"}


def test_an_empty_database_stays_empty(m0_db: Settings) -> None:
    migrations.upgrade(m0_db)
    assert _roles(m0_db) == {}
