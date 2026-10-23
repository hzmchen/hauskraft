# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E03-04: every write asks the policy first through the unit of work."""

import logging

import pytest

from hauskraft_core.policy import Decision, DenyAllPolicy, NoOpPolicy, Policy, RolePolicy, policy_from_settings
from hauskraft_core.settings import Settings
from hauskraft_core.uow import UnitOfWork, current_uow
from hauskraft_sdk import Actor, DataClass, ResourceRef
from hauskraft_sdk.errors import PolicyDeniedError

pytestmark = pytest.mark.unit

ACTOR = Actor(id="0199f390-1111-7aaa-8bbb-cccccccccccc", role="adult", display_name="Demo Adult")


class SpyPolicy:
    def __init__(self, decision: Decision = Decision.ALLOW) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.decision = decision

    async def authorize(
        self, actor: Actor, action: str, resource: ResourceRef, data_class: DataClass | str, capability: str
    ) -> Decision:
        self.calls.append((actor, action, resource, data_class, capability))
        return self.decision


class FakeSession:
    def __init__(self) -> None:
        self.events: list[str] = []

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.events.append("close")

    async def commit(self) -> None:
        self.events.append("commit")

    async def rollback(self) -> None:
        self.events.append("rollback")

    async def close(self) -> None:
        self.events.append("close")


def _uow(policy: Policy, session: FakeSession) -> UnitOfWork:
    return UnitOfWork(lambda: session, policy, Settings(env="test"))  # type: ignore[arg-type, return-value]


def test_policy_protocol_is_structural() -> None:
    assert isinstance(NoOpPolicy(), Policy)
    assert isinstance(DenyAllPolicy(), Policy)
    assert isinstance(SpyPolicy(), Policy)


@pytest.mark.parametrize(("name", "cls"), [("roles", RolePolicy), ("noop", NoOpPolicy), ("deny_all", DenyAllPolicy)])
def test_policy_chosen_by_setting(name: str, cls: type) -> None:
    assert isinstance(policy_from_settings(Settings(env="test", policy=name)), cls)


async def test_noop_allows_and_logs_at_debug(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="hauskraft.policy")
    decision = await NoOpPolicy().authorize(ACTOR, "task.create", ResourceRef("Task"), "household", "graph:write:Task")
    assert decision is Decision.ALLOW
    assert any("policy.allow" in str(r.msg) for r in caplog.records if r.name == "hauskraft.policy")


async def test_unit_of_work_forwards_to_the_policy_and_remembers_the_actor() -> None:
    spy, session = SpyPolicy(), FakeSession()
    resource = ResourceRef("Task", "t1")
    async with _uow(spy, session) as uow:
        assert current_uow() is uow
        await uow.authorize(ACTOR, "task.update", resource, DataClass.HOUSEHOLD, "graph:write:Task")
        assert uow.actor == ACTOR
    assert spy.calls == [(ACTOR, "task.update", resource, DataClass.HOUSEHOLD, "graph:write:Task")]
    assert session.events == ["commit", "close"]
    with pytest.raises(LookupError):
        current_uow()


async def test_denied_write_raises_and_rolls_back() -> None:
    session = FakeSession()
    with pytest.raises(PolicyDeniedError) as err:
        async with _uow(SpyPolicy(Decision.DENY), session) as uow:
            await uow.authorize(ACTOR, "task.delete", ResourceRef("Task", "t1"), "household", "graph:write:Task")
            pytest.fail("must not get here")
    assert err.value.status == 403
    assert err.value.code == "policy_denied"
    assert session.events == ["rollback", "close"]


async def test_any_error_rolls_back() -> None:
    session = FakeSession()
    with pytest.raises(RuntimeError):
        async with _uow(NoOpPolicy(), session):
            raise RuntimeError("boom")
    assert "commit" not in session.events
    assert "rollback" in session.events
