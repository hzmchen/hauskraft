# SPDX-License-Identifier: AGPL-3.0-or-later
"""Core's implementation of ``hauskraft_sdk.PluginContext`` (M0S-E06-03).

``emit`` uses the plugin id as CloudEvents ``source``. Using a capability or data class the manifest did not
declare logs a ``governance.undeclared`` warning; M0* records but does not enforce (spec §5.4, §5.5).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from hauskraft_core.auth.deps import current_actor
from hauskraft_core.events import outbox
from hauskraft_core.logging import get_logger
from hauskraft_core.uow import UnitOfWork, current_uow
from hauskraft_sdk import Actor, DataClass, ResourceRef
from hauskraft_sdk.errors import PolicyDeniedError

if TYPE_CHECKING:
    from fastapi import FastAPI

_governance = get_logger("hauskraft.governance")


class CorePluginContext:
    def __init__(self, plugin_id: str, manifest: Mapping[str, Any], app: FastAPI) -> None:
        self.plugin_id = plugin_id
        self.logger = logging.getLogger(f"hauskraft.plugin.{plugin_id}")
        self.config: Mapping[str, Any] = {}
        self._manifest = manifest
        self._app = app
        # A FastAPI dependency: plugins write `actor: Actor = Depends(ctx.current_actor)`.
        self.current_actor: Callable[..., Awaitable[Actor]] = current_actor

    def _declared(self, key: str) -> set[str]:
        if key == "capabilities":
            return set(self._manifest.get("capabilities") or [])
        return set((self._manifest.get("data_classes") or {}).get(key) or [])

    def _undeclared(self, what: str, value: str) -> None:
        _governance.warning("governance.undeclared", plugin_id=self.plugin_id, what=what, value=value)

    @asynccontextmanager
    async def db_session(self) -> AsyncIterator[AsyncSession]:
        state = self._app.state
        async with UnitOfWork(state.sessionmaker, state.policy, state.settings) as uow:
            yield uow.session

    async def authorize(
        self, actor: Actor, action: str, resource: ResourceRef, data_class: DataClass | str, capability: str
    ) -> None:
        if capability not in self._declared("capabilities") and not any(
            capability.startswith(c.removesuffix("*")) for c in self._declared("capabilities") if c.endswith("*")
        ):
            self._undeclared("capability", capability)
        try:
            uow = current_uow()
        except LookupError:
            decision = await self._app.state.policy.authorize(actor, action, resource, data_class, capability)
            if decision != "allow":
                raise PolicyDeniedError(action) from None
            return
        await uow.authorize(actor, action, resource, data_class, capability)

    async def emit(self, event_type: str, subject: str, data: Any, data_class: DataClass | str) -> str:
        if str(DataClass(data_class)) not in self._declared("emits"):
            self._undeclared("emitted data class", str(data_class))
        return await outbox.emit(event_type, subject, data, data_class, source=self.plugin_id)
