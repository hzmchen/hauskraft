# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit of work: one async session, one transaction, one commit (M0S-E03-04, ADR-0006/0007).

Writes go through ``authorize()`` first; the actor it was called with becomes the event actor. Events are
appended to the same transaction through ``emit`` (wired by the outbox writer, M0S-E10-02), so a rollback
removes rows and events together.
"""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar, Token
from types import TracebackType
from typing import Self

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from hearthos_core.policy import Decision, Policy
from hearthos_core.settings import Settings
from hearthos_sdk import Actor, DataClass, ResourceRef
from hearthos_sdk.errors import PolicyDeniedError

_current: ContextVar[UnitOfWork | None] = ContextVar("hearthos_uow", default=None)


def current_uow() -> UnitOfWork:
    uow = _current.get()
    if uow is None:
        raise LookupError("no active unit of work")
    return uow


class UnitOfWork:
    def __init__(self, session_factory: Callable[[], AsyncSession], policy: Policy, settings: Settings) -> None:
        self._session_factory = session_factory
        self.policy = policy
        self.settings = settings
        self.actor: Actor | None = None
        self._session: AsyncSession | None = None
        self._token: Token[UnitOfWork | None] | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("unit of work is not active")
        return self._session

    async def authorize(
        self, actor: Actor, action: str, resource: ResourceRef, data_class: DataClass | str, capability: str
    ) -> None:
        decision = await self.policy.authorize(actor, action, resource, data_class, capability)
        if decision is not Decision.ALLOW:
            raise PolicyDeniedError(action)
        self.actor = actor

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()  # the transaction begins with the first statement
        self._token = _current.set(self)
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        session = self.session
        try:
            if exc_type is None:
                await session.commit()
            else:
                await session.rollback()
        finally:
            await session.close()
            if self._token is not None:
                _current.reset(self._token)
            self._session = None
            self._token = None


def unit_of_work(request: Request) -> UnitOfWork:
    """FastAPI dependency: a fresh, not yet started unit of work (use it with ``async with``)."""
    app = request.app
    return UnitOfWork(app.state.sessionmaker, app.state.policy, app.state.settings)
