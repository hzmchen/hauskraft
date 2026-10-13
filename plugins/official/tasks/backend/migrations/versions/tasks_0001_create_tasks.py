# SPDX-License-Identifier: MIT
"""Create the tasks table (M0S-E07-01). Plugin branch org.hearthos.tasks, after core's users table.

Revision ID: tasks_0001
Revises:
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "tasks_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = ("org.hearthos.tasks",)
depends_on: str | Sequence[str] | None = "0002_core_tables"

TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("done", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("done_at", TZ, nullable=True),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("data_class", sa.Text(), server_default="household", nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", TZ, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TZ, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("char_length(btrim(title)) BETWEEN 1 AND 200", name=op.f("ck_tasks_title_length")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_tasks_created_by_users")),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name=op.f("fk_tasks_updated_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
    )
    op.create_index("ix_tasks_done_created_at", "tasks", ["done", sa.text("created_at DESC")])
    op.create_index("ix_tasks_due_on", "tasks", ["due_on"], postgresql_where=sa.text("due_on IS NOT NULL"))


def downgrade() -> None:
    op.drop_index("ix_tasks_due_on", table_name="tasks")
    op.drop_index("ix_tasks_done_created_at", table_name="tasks")
    op.drop_table("tasks")
