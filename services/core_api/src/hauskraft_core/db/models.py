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


class AssistantConversation(Base):
    """A member's chat with the assistant (M2S-E04-01). Private to its user; kept until deleted."""

    __tablename__ = "assistant_conversations"
    __table_args__ = (Index("ix_assistant_conversations_user", "user_id", text("updated_at DESC")),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())


class AssistantRun(Base):
    """One agent execution (spec §8.0): a chat turn, a skill run or a connection test. Runs without a conversation
    (skills now, schedules later) have ``conversation_id`` NULL."""

    __tablename__ = "assistant_runs"
    __table_args__ = (
        CheckConstraint("kind IN ('chat', 'skill', 'test')", name="kind_known"),
        CheckConstraint("status IN ('running', 'awaiting_confirmation', 'done', 'failed')", name="status_known"),
        Index("ix_assistant_runs_user_skill", "user_id", "skill_id", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assistant_conversations.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(Text)
    run_kind: Mapped[str] = mapped_column(Text, default="interactive", server_default="interactive")
    channel: Mapped[str] = mapped_column(Text, default="text", server_default="text")
    status: Mapped[str] = mapped_column(Text, default="running", server_default="running")
    skill_id: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    tools_hash: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(Text)
    history: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    pending: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    decisions: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    output: Mapped[Any] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())
    finished_at: Mapped[dt.datetime | None] = mapped_column(TIMESTAMPTZ)


class AssistantMessage(Base):
    """A visible chat message: the member's text or the assistant's answer."""

    __tablename__ = "assistant_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="role_known"),
        Index("ix_assistant_messages_conversation", "conversation_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assistant_conversations.id", ondelete="CASCADE"))
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assistant_runs.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())


class AssistantAction(Base):
    """A call of a tool that is not read-only, with its outcome and, where the tool declares one, its inverse."""

    __tablename__ = "assistant_actions"
    __table_args__ = (
        CheckConstraint("status IN ('done', 'failed', 'denied', 'undone')", name="status_known"),
        Index("ix_assistant_actions_run", "run_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assistant_runs.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    tool: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    summary_key: Mapped[str | None] = mapped_column(Text)
    record: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    undo: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())


class AssistantUsage(Base):
    """One model request (M2S-E08-01). Kept when its chat is deleted; tokens are NULL when the server reported none."""

    __tablename__ = "assistant_usage"
    __table_args__ = (Index("ix_assistant_usage_time", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assistant_runs.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    input_tokens: Mapped[int | None] = mapped_column()
    output_tokens: Mapped[int | None] = mapped_column()
    cached_tokens: Mapped[int | None] = mapped_column()
    status: Mapped[str] = mapped_column(Text, default="ok", server_default="ok")
    created_at: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())


__all__ = [
    "AssistantAction",
    "AssistantConversation",
    "AssistantMessage",
    "AssistantRun",
    "AssistantUsage",
    "DashboardLayout",
    "DeploymentSetting",
    "OutboxEvent",
    "PluginRecord",
    "Session",
    "User",
    "UserRole",
]
