# SPDX-License-Identifier: AGPL-3.0-or-later
"""M1S-E02-01, M2S-E03-01: the static role permission table behind ``authorize()`` (ADR 0016, spec §2.3)."""

import pytest

from hauskraft_core.policy import Decision, Policy, RolePolicy
from hauskraft_sdk import Actor, ResourceRef

pytestmark = pytest.mark.unit

OWNER = Actor(id="0199f390-1111-7aaa-8bbb-000000000001", role="owner", display_name="Mia")
ADULT = Actor(id="0199f390-1111-7aaa-8bbb-000000000002", role="adult", display_name="Alex")
SYSTEM = Actor(id="system", role="owner", display_name="System", kind="system")

BOTH = [
    "task.read",
    "task.create",
    "task.update",
    "task.delete",
    "dashboard.layout.set",
    "session.create",
    "session.revoke",
    "user.update_self",
    "user.change_password",
    "assistant.use",
]
OWNER_ONLY = [
    "settings.theme.set",
    "settings.household.set",
    "plugin.toggle",
    "user.list",
    "user.create",
    "user.update",
    "user.deactivate",
    "user.reactivate",
    "user.reset_password",
    "assistant.configure",
    "assistant.usage.read",
]
SYSTEM_ONLY = ["plugin.sync", "setup.complete"]


async def _decide(actor: Actor, action: str) -> Decision:
    return await RolePolicy().authorize(actor, action, ResourceRef("Thing"), "household", "graph:write:Thing")


def test_role_policy_is_a_policy() -> None:
    assert isinstance(RolePolicy(), Policy)


@pytest.mark.parametrize("action", BOTH)
async def test_both_roles_may(action: str) -> None:
    assert await _decide(OWNER, action) is Decision.ALLOW
    assert await _decide(ADULT, action) is Decision.ALLOW


@pytest.mark.parametrize("action", OWNER_ONLY)
async def test_only_owners_may(action: str) -> None:
    assert await _decide(OWNER, action) is Decision.ALLOW
    assert await _decide(ADULT, action) is Decision.DENY


@pytest.mark.parametrize("action", SYSTEM_ONLY)
async def test_only_the_system_actor_may(action: str) -> None:
    assert await _decide(SYSTEM, action) is Decision.ALLOW
    assert await _decide(OWNER, action) is Decision.DENY
    assert await _decide(ADULT, action) is Decision.DENY


@pytest.mark.parametrize("action", [*BOTH, *OWNER_ONLY])
async def test_the_system_actor_acts_as_owner(action: str) -> None:
    assert await _decide(SYSTEM, action) is Decision.ALLOW


@pytest.mark.parametrize("actor", [OWNER, ADULT, SYSTEM], ids=lambda a: a.role + "/" + a.kind)
async def test_unknown_actions_are_denied(actor: Actor) -> None:
    assert await _decide(actor, "household.burn_down") is Decision.DENY


@pytest.mark.parametrize("role", ["teen", "kid", "guest", ""])
async def test_roles_not_enabled_get_nothing(role: str) -> None:
    actor = Actor(id="0199f390-1111-7aaa-8bbb-000000000003", role=role)
    for action in [*BOTH, *OWNER_ONLY]:
        assert await _decide(actor, action) is Decision.DENY


def test_permissions_for_lists_the_table_rows_sorted() -> None:
    """M1S-E02-04: Session.permissions comes from the same table as RolePolicy."""
    from hauskraft_core.policy import permissions_for

    assert permissions_for("owner") == sorted([*BOTH, *OWNER_ONLY])
    assert permissions_for("adult") == sorted(BOTH)
    assert permissions_for("kid") == []
