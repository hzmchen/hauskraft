# SPDX-License-Identifier: AGPL-3.0-or-later
"""A public id per session for the sessions list (M1S-E05-02).

The primary key is sha256(cookie token) and must never leave the server; members address their sessions by this
opaque id instead.

Revision ID: 0005_session_public_id
Revises: 0004_first_owner
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_session_public_id"
down_revision: str | Sequence[str] | None = "0004_first_owner"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sessions", sa.Column("public_id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False)
    )
    op.create_unique_constraint(op.f("uq_sessions_public_id"), "sessions", ["public_id"])


def downgrade() -> None:
    op.drop_constraint(op.f("uq_sessions_public_id"), "sessions", type_="unique")
    op.drop_column("sessions", "public_id")
