# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E04-04: the shared database fixtures (pytest plugin ``hearthos_core.testing``).

The two ordered tests prove isolation: what one test writes is gone in the next.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from hearthos_core.db import migrations
from hearthos_core.settings import Settings

pytestmark = pytest.mark.integration


def test_database_is_migrated_to_heads(db_settings: Settings) -> None:
    assert migrations.is_at_heads(db_settings)


async def test_writes_inside_a_test_1(db_session: AsyncSession) -> None:
    await db_session.execute(text("CREATE TABLE isolation_probe (id int PRIMARY KEY)"))
    await db_session.execute(text("INSERT INTO isolation_probe VALUES (1)"))
    await db_session.commit()  # a commit inside the test still ends up rolled back
    assert (await db_session.execute(text("SELECT count(*) FROM isolation_probe"))).scalar_one() == 1


async def test_writes_inside_a_test_2_are_gone(db_session: AsyncSession) -> None:
    exists = await db_session.execute(text("SELECT to_regclass('public.isolation_probe') IS NOT NULL"))
    assert exists.scalar_one() is False


async def test_session_is_usable_after_a_rollback(db_session: AsyncSession) -> None:
    await db_session.execute(text("SELECT 1"))
    await db_session.rollback()
    assert (await db_session.execute(text("SELECT 2"))).scalar_one() == 2
