# SPDX-License-Identifier: AGPL-3.0-or-later
"""Home Assistant bridge seam (spec §7.1).

Home Assistant counts as a third-party integration in M0* (decision D8), so only the protocol and a
``NullBridge`` exist. The real ``ha-bridge`` (WebSocket client, entity cache, service calls) replaces
``NullBridge`` in M1 without changing callers.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class HomeAssistantUnavailableError(RuntimeError):
    """Raised when an operation needs Home Assistant but no bridge is connected."""


@dataclass(frozen=True, slots=True)
class EntityState:
    entity_id: str
    state: str
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class HomeAssistantEvent:
    event_type: str
    data: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class HomeAssistantBridge(Protocol):
    """What the cockpit needs from Home Assistant."""

    @property
    def connected(self) -> bool: ...

    async def get_states(self) -> list[EntityState]: ...

    def subscribe_events(self, event_type: str) -> AsyncIterator[HomeAssistantEvent]: ...

    async def call_service(self, domain: str, service: str, data: Mapping[str, Any]) -> None: ...


class NullBridge:
    """A bridge that is never connected. It performs no I/O of any kind."""

    @property
    def connected(self) -> bool:
        return False

    async def get_states(self) -> list[EntityState]:
        return []

    async def subscribe_events(self, event_type: str) -> AsyncIterator[HomeAssistantEvent]:
        return
        yield  # pragma: no cover - makes this an async generator that yields nothing

    async def call_service(self, domain: str, service: str, data: Mapping[str, Any]) -> None:
        raise HomeAssistantUnavailableError(
            f"cannot call {domain}.{service}: Home Assistant is not connected in M0* (NullBridge)"
        )
