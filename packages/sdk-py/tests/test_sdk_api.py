# SPDX-License-Identifier: MIT
"""M0S-E06-02: the public, minimal Python SDK surface for plugins."""

from __future__ import annotations

import logging
import subprocess
import sys
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest
from fastapi import APIRouter
from sqlalchemy import MetaData

import hauskraft_sdk
from hauskraft_sdk import (
    HAUSKRAFT_API_VERSION,
    Actor,
    DataClass,
    Plugin,
    PluginContext,
    PluginRegistration,
    ResourceRef,
)
from hauskraft_sdk.errors import ConflictError, HauskraftError, NotFoundError, PolicyDeniedError

pytestmark = pytest.mark.unit


def test_api_version_is_semver() -> None:
    assert HAUSKRAFT_API_VERSION == "0.1.0"


def test_public_names() -> None:
    for name in (
        "Plugin",
        "PluginRegistration",
        "PluginContext",
        "Actor",
        "DataClass",
        "ResourceRef",
        "HAUSKRAFT_API_VERSION",
    ):
        assert name in hauskraft_sdk.__all__


def test_data_classes_are_ordered() -> None:
    assert list(DataClass) == ["public", "household", "personal", "financial", "tenant", "child", "health", "secret"]
    assert DataClass.PUBLIC < DataClass.HOUSEHOLD < DataClass.SECRET
    assert max(DataClass.HEALTH, DataClass.FINANCIAL, DataClass.CHILD) is DataClass.HEALTH


def test_actor_and_resource_are_immutable_values() -> None:
    actor = Actor(id="0199f390-1111-7aaa-8bbb-cccccccccccc", role="adult", display_name="Demo Adult")
    assert actor.kind == "user"
    with pytest.raises(AttributeError):
        actor.role = "owner"  # type: ignore[misc]
    assert ResourceRef("Task", "x") == ResourceRef(type="Task", id="x")


def test_registration_holds_router_metadata_and_seed() -> None:
    async def seed(ctx: PluginContext, fixture: Mapping[str, Any]) -> None:
        return None

    reg = PluginRegistration(router=APIRouter(), metadata=MetaData(), seed=seed)
    assert reg.seed is seed
    assert PluginRegistration(router=APIRouter()).metadata is None


class _FakeContext:
    plugin_id = "org.example.fake"
    logger = logging.getLogger("fake")
    config: Mapping[str, Any] = {}

    async def current_actor(self) -> Actor:
        return Actor(id="a", role="adult", display_name="A")

    @asynccontextmanager
    async def db_session(self) -> AsyncIterator[Any]:
        yield object()

    async def authorize(
        self, actor: Actor, action: str, resource: ResourceRef, data_class: DataClass | str, capability: str
    ) -> None:
        return None

    async def emit(self, event_type: str, subject: str, data: Any, data_class: DataClass | str) -> str:
        return "event-id"


class _FakePlugin:
    id = "org.example.fake"

    def register(self, ctx: PluginContext) -> PluginRegistration:
        return PluginRegistration(router=APIRouter())


def test_protocols_are_structural() -> None:
    assert isinstance(_FakeContext(), PluginContext)
    assert isinstance(_FakePlugin(), Plugin)


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (NotFoundError("Task not found"), 404, "not_found"),
        (ConflictError("version_conflict", "Task changed"), 409, "version_conflict"),
        (PolicyDeniedError("task.delete"), 403, "policy_denied"),
    ],
)
def test_errors_carry_status_and_code(error: HauskraftError, status: int, code: str) -> None:
    assert error.status == status
    assert error.code == code
    assert isinstance(error, HauskraftError)


def test_sdk_ships_type_information() -> None:
    assert (Path(hauskraft_sdk.__file__).parent / "py.typed").exists()


def test_importing_the_sdk_never_imports_core() -> None:
    code = (
        "import sys, hauskraft_sdk, hauskraft_sdk.events; "
        "print(any(m.startswith('hauskraft_core') for m in sys.modules))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.strip() == "False"
