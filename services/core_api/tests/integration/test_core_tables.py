# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E04-02: core tables match the contract in E04."""

import datetime as dt
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hauskraft_core.db import migrations
from hauskraft_core.db.models import DashboardLayout, DeploymentSetting, PluginRecord, Session, User, UserRole
from hauskraft_core.settings import Settings

pytestmark = pytest.mark.integration
NOW = dt.datetime(2026, 10, 12, 9, 0, tzinfo=dt.UTC)


def _user(username: str = "demo") -> User:
    return User(username=username, display_name="Demo Adult", password_hash="$argon2id$fake")


async def test_user_defaults_and_uuid7(db_session: AsyncSession) -> None:
    user = _user()
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    assert user.id.version == 7
    assert user.role is UserRole.ADULT
    assert user.locale == "en"
    assert user.is_active is True
    assert user.data_class == "personal"
    assert user.created_at.tzinfo is not None
    assert user.external_subject is None


async def test_role_enum_has_all_eight_roles(db_session: AsyncSession) -> None:
    rows = await db_session.execute(text("SELECT unnest(enum_range(NULL::user_role))::text"))
    assert [r[0] for r in rows] == ["owner", "adult", "teen", "kid", "caregiver", "property_manager", "tenant", "guest"]
    assert [r.value for r in UserRole] == [
        "owner",
        "adult",
        "teen",
        "kid",
        "caregiver",
        "property_manager",
        "tenant",
        "guest",
    ]


@pytest.mark.parametrize(("column", "value"), [("locale", "fr"), ("username", "Demo")])
async def test_user_checks(db_session: AsyncSession, column: str, value: str) -> None:
    user = _user("checks")
    setattr(user, column, value)
    db_session.add(user)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_username_is_unique(db_session: AsyncSession) -> None:
    db_session.add(_user("same"))
    await db_session.flush()
    db_session.add(_user("same"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_sessions_cascade_with_their_user(db_session: AsyncSession) -> None:
    user = _user("sess")
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        Session(id="a" * 64, user_id=user.id, csrf_token="c", expires_at=NOW, ip="192.0.2.10", user_agent="pytest")
    )
    await db_session.flush()
    assert (await db_session.get(Session, "a" * 64)) is not None
    await db_session.delete(user)
    await db_session.flush()
    db_session.expunge_all()
    assert (await db_session.get(Session, "a" * 64)) is None


async def test_plugin_record(db_session: AsyncSession) -> None:
    db_session.add(
        PluginRecord(
            id="org.example.recordprobe",
            version="0.1.0",
            kind="inprocess",
            manifest={"id": "org.example.recordprobe"},
            manifest_sha256="0" * 64,
        )
    )
    await db_session.flush()
    record = await db_session.get(PluginRecord, "org.example.recordprobe")
    assert record is not None
    assert record.enabled is True
    assert record.load_error is None
    assert record.manifest["id"] == "org.example.recordprobe"


async def test_deployment_setting_upsert_by_key(db_session: AsyncSession) -> None:
    for value in ("dev.hauskraft.theme.default", "dev.hauskraft.theme.hackspace"):
        stmt = insert(DeploymentSetting).values(key="theme_id", value=value, updated_at=NOW)
        await db_session.execute(
            stmt.on_conflict_do_update(index_elements=["key"], set_={"value": value, "updated_at": NOW})
        )
    rows = (await db_session.execute(select(DeploymentSetting))).scalars().all()
    assert [(r.key, r.value) for r in rows] == [("theme_id", "dev.hauskraft.theme.hackspace")]


async def test_dashboard_layout_per_user_and_dashboard(db_session: AsyncSession) -> None:
    user = _user("dash")
    db_session.add(user)
    await db_session.flush()
    cell = {"i": "a", "plugin_id": "dev.hauskraft.tasks", "widget_id": "tasks.list", "x": 0, "y": 0, "w": 4, "h": 6}
    db_session.add(DashboardLayout(user_id=user.id, layout=[cell]))
    await db_session.flush()
    layout = await db_session.get(DashboardLayout, (user.id, "today"))
    assert layout is not None
    assert layout.layout == [cell]


def test_models_match_migrations(db_settings: Settings) -> None:
    migrations.check(db_settings)


def test_uuid7_helper_is_time_ordered() -> None:
    from hauskraft_core.db.ids import new_id

    ids = [new_id() for _ in range(50)]
    assert all(isinstance(i, uuid.UUID) and i.version == 7 for i in ids)
    assert ids == sorted(ids)
