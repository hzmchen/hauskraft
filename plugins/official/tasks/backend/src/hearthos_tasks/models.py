# SPDX-License-Identifier: MIT
"""The ``tasks`` table, owned by the plugin (M0S-E07-01). Contract: docs/backlog/m0-star/E07-tasks-plugin.md."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    MetaData,
    Table,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

# Core's users table, declared only so foreign keys resolve. It is never created or compared from here
# (``info["hearthos_reference_only"]``); core owns it.
users = Table(
    "users",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("display_name", Text),
    info={"hearthos_reference_only": True},
)

TIMESTAMPTZ = DateTime(timezone=True)


class Base(DeclarativeBase):
    metadata = metadata


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("char_length(btrim(title)) BETWEEN 1 AND 200", name="title_length"),
        Index("ix_tasks_done_created_at", "done", text("created_at DESC")),
        Index("ix_tasks_due_on", "due_on", postgresql_where=text("due_on IS NOT NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    done: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    done_at: Mapped[dt.datetime | None] = mapped_column(TIMESTAMPTZ)
    due_on: Mapped[dt.date | None] = mapped_column(Date)
    data_class: Mapped[str] = mapped_column(Text, default="household", server_default="household")
    version: Mapped[int] = mapped_column(default=1, server_default=text("1"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())
