# SPDX-License-Identifier: AGPL-3.0-or-later
"""Core branch base. Later core revisions build on it; plugin branches depend on core heads.

Revision ID: 0001_core_base
Revises:
Create Date: 2026-10-12
"""

from collections.abc import Sequence

revision: str = "0001_core_base"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = ("core",)
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
