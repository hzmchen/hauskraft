# SPDX-License-Identifier: AGPL-3.0-or-later
"""The ``authorize()`` seam (M0S-E03-04, ADR-0006, spec §8.3).

Every write to a domain entity or deployment setting asks the policy first. M0* uses ``NoOpPolicy``; Cedar
replaces it in M1 without touching handlers. ``Actor`` and ``ResourceRef`` come from the SDK because plugins
pass them to ``PluginContext.authorize``.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from hauskraft_core.logging import get_logger
from hauskraft_core.settings import Settings
from hauskraft_sdk import Actor, DataClass, ResourceRef

__all__ = ["Actor", "Decision", "DenyAllPolicy", "NoOpPolicy", "Policy", "ResourceRef", "policy_from_settings"]

_log = get_logger("hauskraft.policy")


class Decision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


@runtime_checkable
class Policy(Protocol):
    async def authorize(
        self, actor: Actor, action: str, resource: ResourceRef, data_class: DataClass | str, capability: str
    ) -> Decision: ...


class NoOpPolicy:
    """Allows everything (M0*), logging each decision at debug level."""

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
    return DenyAllPolicy() if settings.policy == "deny_all" else NoOpPolicy()
