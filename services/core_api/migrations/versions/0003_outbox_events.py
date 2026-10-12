# SPDX-License-Identifier: AGPL-3.0-or-later
"""Append-only outbox_events table (M0S-E04-03, ADR-0007).

Revision ID: 0003_outbox_events
Revises: 0002_core_tables
Create Date: 2026-10-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_outbox_events"
down_revision: str | Sequence[str] | None = "0002_core_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TZ = sa.DateTime(timezone=True)

APPEND_ONLY = """
CREATE FUNCTION outbox_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
        RAISE EXCEPTION 'outbox_events is append-only: % is not allowed', TG_OP;
    END IF;
    IF (NEW.id, NEW.type, NEW.source, NEW.subject, NEW.data_class, NEW.actor_id, NEW.time, NEW.envelope)
       IS DISTINCT FROM
       (OLD.id, OLD.type, OLD.source, OLD.subject, OLD.data_class, OLD.actor_id, OLD.time, OLD.envelope) THEN
        RAISE EXCEPTION 'outbox_events is append-only: only published_at and attempts may change';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER outbox_append_only_rows BEFORE UPDATE OR DELETE ON outbox_events
    FOR EACH ROW EXECUTE FUNCTION outbox_append_only();
CREATE TRIGGER outbox_append_only_truncate BEFORE TRUNCATE ON outbox_events
    FOR EACH STATEMENT EXECUTE FUNCTION outbox_append_only();
"""


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("data_class", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("time", TZ, nullable=False),
        sa.Column("envelope", postgresql.JSONB(), nullable=False),
        sa.Column("published_at", TZ, nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], name=op.f("fk_outbox_events_actor_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_events")),
    )
    op.create_index(
        "ix_outbox_events_unpublished",
        "outbox_events",
        ["published_at"],
        postgresql_where=sa.text("published_at IS NULL"),
    )
    op.create_index("ix_outbox_events_time", "outbox_events", [sa.text("time DESC")])
    op.execute(APPEND_ONLY)


def downgrade() -> None:
    op.execute("DROP TRIGGER outbox_append_only_truncate ON outbox_events")
    op.execute("DROP TRIGGER outbox_append_only_rows ON outbox_events")
    op.drop_index("ix_outbox_events_time", table_name="outbox_events")
    op.drop_index("ix_outbox_events_unpublished", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.execute("DROP FUNCTION outbox_append_only()")
