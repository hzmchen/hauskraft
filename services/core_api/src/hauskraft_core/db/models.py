# SPDX-License-Identifier: AGPL-3.0-or-later
"""Core tables (M0S-E04-02). Contract: docs/backlog/m0-star/E04-database-and-migrations.md."""

from __future__ import annotations

import datetime as dt
import enum
import uuid
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from hauskraft_core.db.base import Base
from hauskraft_core.db.ids import new_id


class UserRole(enum.StrEnum):
    """The full role enum (spec §2.1). Only ``owner`` and ``adult`` can be created (M1*, ADR 0016)."""

    OWNER = "owner"
    ADULT = "adult"
    TEEN = "teen"
    KID = "kid"
    CAREGIVER = "caregiver"
    PROPERTY_MANAGER = "property_manager"
    TENANT = "tenant"
    GUEST = "guest"


USER_ROLE = Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e])
TIMESTAMPTZ = DateTime(timezone=True)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("locale IN ('en', 'de')", name="locale"),
        CheckConstraint("username = lower(username)", name="username_lowercase"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(Text, unique=True)
    display_name: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[UserRole] = mapped_column(USER_ROLE, default=UserRole.ADULT, server_default=UserRole.ADULT.value)
    locale: Mapped[str] = mapped_column(Text, default="en", server_default="en")
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    must_change_password: Mapped[bool] = mapped_column(default=False, server_default=text("false"))  # M1S-E07-01
    external_subject: Mapped[str | None] = mapped_column(Text, unique=True)  # OIDC seam (M1)
    data_class: Mapped[str] = mapped_column(Text, default="personal", server_default="personal")
    created_at: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now(), onupdate=func.now())
    last_login_at: Mapped[dt.datetime | None] = mapped_column(TIMESTAMPTZ)


class Session(Base):
    """A server-side session. ``id`` is sha256(token) in hex; the raw token lives only in the cookie."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    public_id: Mapped[uuid.UUID] = mapped_column(
        unique=True, default=new_id, server_default=text("gen_random_uuid()")
    )  # what members see and send (M1S-E05-02); ``id`` never leaves the server
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf_token: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())
    last_seen_at: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())
    expires_at: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(TIMESTAMPTZ)
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(INET)


class PluginRecord(Base):
    __tablename__ = "plugins"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    version: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB)
    manifest_sha256: Mapped[str] = mapped_column(Text)
    loaded_at: Mapped[dt.datetime | None] = mapped_column(TIMESTAMPTZ)
    load_error: Mapped[str | None] = mapped_column(Text)


class DeploymentSetting(Base):
    __tablename__ = "deployment_settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now(), onupdate=func.now())


class DashboardLayout(Base):
    __tablename__ = "dashboard_layouts"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    dashboard_id: Mapped[str] = mapped_column(Text, primary_key=True, default="today", server_default="today")
    layout: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    updated_at: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now(), onupdate=func.now())


class OutboxEvent(Base):
    """One CloudEvent per write, appended in the same transaction (ADR-0007). Append-only by trigger."""

    __tablename__ = "outbox_events"
    __table_args__ = (
        Index("ix_outbox_events_unpublished", "published_at", postgresql_where=text("published_at IS NULL")),
        Index("ix_outbox_events_time", text("time DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)  # = CloudEvent id
    type: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    subject: Mapped[str | None] = mapped_column(Text)
    data_class: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    time: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ)
    envelope: Mapped[dict[str, Any]] = mapped_column(JSONB)
    published_at: Mapped[dt.datetime | None] = mapped_column(TIMESTAMPTZ)
    attempts: Mapped[int] = mapped_column(default=0, server_default=text("0"))


__all__ = ["DashboardLayout", "DeploymentSetting", "OutboxEvent", "PluginRecord", "Session", "User", "UserRole"]
