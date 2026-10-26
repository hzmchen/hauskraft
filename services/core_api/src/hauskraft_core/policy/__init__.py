# SPDX-License-Identifier: AGPL-3.0-or-later
"""The ``authorize()`` seam (M0S-E03-04, ADR-0006, spec §8.3).

Every write to a domain entity or deployment setting asks the policy first. M1* uses ``RolePolicy``, a static
permission table (ADR 0016); Cedar can replace it later without touching handlers. ``Actor`` and ``ResourceRef``
come from the SDK because plugins pass them to ``PluginContext.authorize``.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Protocol, runtime_checkable

from hauskraft_core.logging import get_logger
from hauskraft_core.settings import Settings
from hauskraft_sdk import Actor, DataClass, ResourceRef

__all__ = [
    "PERMISSIONS",
    "Actor",
    "Decision",
    "DenyAllPolicy",
    "NoOpPolicy",
    "Policy",
    "ResourceRef",
    "RolePolicy",
    "permissions_for",
    "policy_from_settings",
]

_log = get_logger("hauskraft.policy")


class Decision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


@runtime_checkable
class Policy(Protocol):
    async def authorize(
        self, actor: Actor, action: str, resource: ResourceRef, data_class: DataClass | str, capability: str
    ) -> Decision: ...


_BOTH = frozenset({"owner", "adult"})
_OWNER = frozenset({"owner"})

PERMISSIONS: Mapping[str, frozenset[str]] = {
    "task.read": _BOTH,
    "task.create": _BOTH,
    "task.update": _BOTH,
    "task.delete": _BOTH,
    "dashboard.layout.set": _BOTH,
    "session.create": _BOTH,
    "session.revoke": _BOTH,
    "user.update_self": _BOTH,
    "user.change_password": _BOTH,
    "assistant.use": _BOTH,
    "settings.theme.set": _OWNER,
    "settings.household.set": _OWNER,
    "plugin.toggle": _OWNER,
    "user.list": _OWNER,
    "user.create": _OWNER,
    "user.update": _OWNER,
    "user.deactivate": _OWNER,
    "user.reactivate": _OWNER,
    "user.reset_password": _OWNER,
    "assistant.configure": _OWNER,
    "assistant.usage.read": _OWNER,
}
"""Which roles may do what (spec §2.3). Actions that are not listed are denied."""

SYSTEM_ONLY = frozenset({"plugin.sync", "setup.complete"})
"""Actions only the system actor (CLI, seed, plugin sync, setup) may do; it otherwise acts as an owner."""


def permissions_for(role: str) -> list[str]:
    """The sorted actions ``role`` may do, for ``Session.permissions``."""
    return sorted(action for action, roles in PERMISSIONS.items() if role in roles)


class RolePolicy:
    """Allows an action when the actor's role is in its row of ``PERMISSIONS`` (ADR 0016)."""

    async def authorize(
        self, actor: Actor, action: str, resource: ResourceRef, data_class: DataClass | str, capability: str
    ) -> Decision:
        if action in SYSTEM_ONLY:
            allowed = actor.kind == "system"
        else:
            allowed = actor.role in PERMISSIONS.get(action, frozenset())
        if not allowed:
            _log.info("policy.deny", actor_id=actor.id, role=actor.role, action=action, resource_type=resource.type)
            return Decision.DENY
        _log.debug("policy.allow", actor_id=actor.id, role=actor.role, action=action, resource_type=resource.type)
        return Decision.ALLOW


class NoOpPolicy:
    """Allows everything. Test-only since M1* (``HAUSKRAFT_POLICY=noop``), logging each decision at debug level."""

    async def authorize(
        self, actor: Actor, action: str, resource: ResourceRef, data_class: DataClass | str, capability: str
    ) -> Decision:
        _log.debug(
            "policy.allow",
            actor_id=actor.id,
            action=action,
            resource_type=resource.type,
            resource_id=resource.id,
            data_class=str(data_class),
            capability=capability,
        )
        return Decision.ALLOW


class DenyAllPolicy:
    """Denies everything. Test-only (``HAUSKRAFT_POLICY=deny_all``) to prove the seam is wired."""

    async def authorize(
        self, actor: Actor, action: str, resource: ResourceRef, data_class: DataClass | str, capability: str
    ) -> Decision:
        _log.info("policy.deny", actor_id=actor.id, action=action, resource_type=resource.type)
        return Decision.DENY


def policy_from_settings(settings: Settings) -> Policy:
    policies: dict[str, type[Policy]] = {"roles": RolePolicy, "noop": NoOpPolicy, "deny_all": DenyAllPolicy}
    return policies[settings.policy]()
