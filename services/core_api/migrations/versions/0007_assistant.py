# SPDX-License-Identifier: AGPL-3.0-or-later
"""Assistant conversations, runs, messages and actions (M2S-E04-01, spec §8.0).

Revision ID: 0007_assistant
Revises: 0006_must_change_password
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_assistant"
down_revision: str | Sequence[str] | None = "0006_must_change_password"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)
EMPTY = sa.text("'[]'::jsonb")


def upgrade() -> None:
    op.create_table(
        "assistant_conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_assistant_conversations_user", "assistant_conversations", ["user_id", sa.text("updated_at DESC")]
    )
    op.create_table(
        "assistant_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("assistant_conversations.id", ondelete="CASCADE")),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("run_kind", sa.Text(), server_default="interactive", nullable=False),
        sa.Column("channel", sa.Text(), server_default="text", nullable=False),
        sa.Column("status", sa.Text(), server_default="running", nullable=False),
        sa.Column("skill_id", sa.Text()),
        sa.Column("model", sa.Text()),
        sa.Column("prompt_version", sa.Text()),
        sa.Column("tools_hash", sa.Text()),
        sa.Column("error_code", sa.Text()),
        sa.Column("history", postgresql.JSONB(), server_default=EMPTY, nullable=False),
        sa.Column("pending", postgresql.JSONB(), server_default=EMPTY, nullable=False),
        sa.Column("decisions", postgresql.JSONB(), server_default=EMPTY, nullable=False),
        sa.Column("output", postgresql.JSONB()),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", TS),
        sa.CheckConstraint("kind IN ('chat', 'skill', 'test')", name="kind_known"),
        sa.CheckConstraint("status IN ('running', 'awaiting_confirmation', 'done', 'failed')", name="status_known"),
    )
    op.create_index(
        "ix_assistant_runs_user_skill", "assistant_runs", ["user_id", "skill_id", sa.text("created_at DESC")]
    )
    op.create_table(
        "assistant_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("assistant_runs.id", ondelete="CASCADE")),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="role_known"),
    )
    op.create_index("ix_assistant_messages_conversation", "assistant_messages", ["conversation_id", "created_at"])
    op.create_table(
        "assistant_actions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("assistant_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("summary_key", sa.Text()),
        sa.Column("record", postgresql.JSONB()),
        sa.Column("undo", postgresql.JSONB()),
        sa.Column("error_code", sa.Text()),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('done', 'failed', 'denied', 'undone')", name="status_known"),
    )
    op.create_index("ix_assistant_actions_run", "assistant_actions", ["run_id", "created_at"])


def downgrade() -> None:
    op.drop_table("assistant_actions")
    op.drop_table("assistant_messages")
    op.drop_table("assistant_runs")
    op.drop_table("assistant_conversations")
