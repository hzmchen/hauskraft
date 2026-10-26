# SPDX-License-Identifier: AGPL-3.0-or-later
"""Assistant usage: one row per model request (M2S-E08-01).

Revision ID: 0008_assistant_usage
Revises: 0007_assistant
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_assistant_usage"
down_revision: str | Sequence[str] | None = "0007_assistant"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assistant_usage",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("assistant_runs.id", ondelete="SET NULL")),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("model", sa.Text()),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("cached_tokens", sa.Integer()),
        sa.Column("status", sa.Text(), server_default="ok", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_assistant_usage_time", "assistant_usage", ["created_at"])


def downgrade() -> None:
    op.drop_table("assistant_usage")
