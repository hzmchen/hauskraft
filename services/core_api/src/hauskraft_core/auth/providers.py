# SPDX-License-Identifier: AGPL-3.0-or-later
"""Identity providers (M0S-E05-04, ADR-0005).

Login asks the configured provider who the credentials belong to; routers never check passwords
themselves. ``LocalPasswordProvider`` serves M0*. ``OidcProvider`` is a stub until M1, when it maps an
OIDC subject to ``users.external_subject``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hauskraft_core.auth.passwords import dummy_verify, verify_password
from hauskraft_core.db.models import User
from hauskraft_core.settings import Settings


@dataclass(frozen=True, slots=True)
class PasswordCredentials:
    username: str
    password: str


@dataclass(frozen=True, slots=True)
class UserRef:
    """The authenticated user, plus a rehashed password when the stored parameters were outdated."""

    user: User
    upgraded_password_hash: str | None = None


@runtime_checkable
class IdentityProvider(Protocol):
    async def authenticate(self, session: AsyncSession, credentials: PasswordCredentials) -> UserRef | None:
        """Return the user for valid credentials, else None. Must not reveal which part was wrong."""
        ...


class LocalPasswordProvider:
    async def authenticate(self, session: AsyncSession, credentials: PasswordCredentials) -> UserRef | None:
        username = credentials.username.strip().lower()
        user = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()
        if user is None or not user.is_active:
            await dummy_verify(credentials.password)  # same work as a real check (timing parity)
            return None
        ok, new_hash = await verify_password(credentials.password, user.password_hash)
        return UserRef(user, new_hash) if ok else None


class OidcProvider:
    """Placeholder for OpenID Connect (built-in, Authelia, Authentik, Keycloak) in M1."""

    async def authenticate(self, session: AsyncSession, credentials: PasswordCredentials) -> UserRef | None:
        raise NotImplementedError("OIDC login arrives in M1 (ADR-0005); use HAUSKRAFT_AUTH_PROVIDER=local")


def provider_from_settings(settings: Settings) -> IdentityProvider:
    return OidcProvider() if settings.auth_provider == "oidc" else LocalPasswordProvider()
