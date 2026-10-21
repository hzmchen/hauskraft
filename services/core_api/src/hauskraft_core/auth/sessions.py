# SPDX-License-Identifier: AGPL-3.0-or-later
"""Server-side sessions (M0S-E05-02, ADR-0005).

The cookie holds a 256-bit random token; the database stores only ``sha256(token)``. Sessions last 14 days,
sliding with use, and end after 7 idle days. Login always creates a new session (rotation).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import secrets
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hearthos_core.db.models import Session, User

COOKIE_NAME = "hearthos_session"
LIFETIME = dt.timedelta(days=14)
IDLE_TIMEOUT = dt.timedelta(days=7)
TOUCH_INTERVAL = dt.timedelta(minutes=1)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii", errors="ignore")).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


async def create(session: AsyncSession, user: User, *, user_agent: str | None, ip: str | None) -> tuple[str, Session]:
    token = new_token()
    current = now()
    row = Session(
        id=token_hash(token),
        user_id=user.id,
        csrf_token=secrets.token_urlsafe(32),
        created_at=current,
        last_seen_at=current,
        expires_at=current + LIFETIME,
        user_agent=(user_agent or "")[:300] or None,
        ip=ip,
    )
    session.add(row)
    await session.flush()
    return token, row


async def revoke(session: AsyncSession, token: str | None) -> None:
    if token:
        await session.execute(
            update(Session)
            .where(Session.id == token_hash(token), Session.revoked_at.is_(None))
            .values(revoked_at=now())
        )


async def resolve(session: AsyncSession, token: str) -> tuple[Session, User] | None:
    """The live session and its active user for a cookie token, sliding the expiry; None if invalid."""
    row = (
        await session.execute(
            select(Session, User).join(User, User.id == Session.user_id).where(Session.id == token_hash(token))
        )
    ).first()
    if row is None:
        return None
    sess, user = row
    current = now()
    if (
        sess.revoked_at is not None
        or sess.expires_at <= current
        or current - sess.last_seen_at > IDLE_TIMEOUT
        or not user.is_active
    ):
        return None
    if current - sess.last_seen_at > TOUCH_INTERVAL:
        sess.last_seen_at = current
        sess.expires_at = current + LIFETIME
        await session.commit()
    return sess, user


def user_id(sess: Session) -> uuid.UUID:
    return sess.user_id
