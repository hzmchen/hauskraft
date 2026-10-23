# SPDX-License-Identifier: AGPL-3.0-or-later
"""Accounts with a temporary password must choose their own first (M1S-E07-01).

Revision ID: 0006_must_change_password
Revises: 0005_session_public_id
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_must_change_password"
down_revision: str | Sequence[str] | None = "0005_session_public_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("must_change_password", sa.Boolean(), server_default=sa.text("false"), nullable=False)
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
