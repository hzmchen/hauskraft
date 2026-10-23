# SPDX-License-Identifier: AGPL-3.0-or-later
"""Give an M0* household an owner (M1S-E02-03, ADR 0016).

If no active account is an owner, the oldest active account (by ``created_at``, then ``id``) becomes one. A
database with an owner, or with no accounts, is left unchanged. Data only: the downgrade keeps the owner.

Revision ID: 0004_first_owner
Revises: 0003_outbox_events
Create Date: 2026-10-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_first_owner"
down_revision: str | Sequence[str] | None = "0003_outbox_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FIRST_OWNER = """
UPDATE users SET role = 'owner'
WHERE id = (SELECT id FROM users WHERE is_active ORDER BY created_at, id LIMIT 1)
  AND NOT EXISTS (SELECT 1 FROM users WHERE is_active AND role = 'owner')
"""


def upgrade() -> None:
    op.execute(FIRST_OWNER)


def downgrade() -> None:
    """Nothing to undo: the role an account had before can't be told from an owner chosen later."""
