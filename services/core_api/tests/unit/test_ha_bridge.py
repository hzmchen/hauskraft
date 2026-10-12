# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E12-03: Home Assistant is third-party in M0*; only a NullBridge exists and it never touches the network."""

import socket
from collections.abc import Iterator
from typing import Any

import pytest

from hearthos_core.integrations.ha import (
    HomeAssistantBridge,
    HomeAssistantUnavailableError,
    NullBridge,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    def refuse(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("NullBridge must not open sockets")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    yield


def test_null_bridge_satisfies_the_protocol() -> None:
    assert isinstance(NullBridge(), HomeAssistantBridge)


@pytest.mark.usefixtures("no_network")
async def test_null_bridge_reads_nothing() -> None:
    bridge = NullBridge()
    assert bridge.connected is False
    assert await bridge.get_states() == []
    assert [e async for e in bridge.subscribe_events("state_changed")] == []


@pytest.mark.usefixtures("no_network")
async def test_null_bridge_refuses_service_calls() -> None:
    with pytest.raises(HomeAssistantUnavailableError):
        await NullBridge().call_service("light", "turn_on", {"entity_id": "light.kitchen"})
