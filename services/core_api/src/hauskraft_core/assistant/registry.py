# SPDX-License-Identifier: AGPL-3.0-or-later
"""The tool registry (M2S-E02-03, ADR 0019): every plugin's agent tools, and the small set each run may use.

``select()`` keeps a tool only if the person's role has its permission (the table of ADR 0016), the owner has not
switched it off, its plugin is enabled, its data class is at most the endpoint's ceiling, and, during a skill run, the
skill lists it. The order is stable (plugin, then name) so providers can cache the prompt prefix. A later
``find_tools`` lookup and the gateway of spec §8.2 attach here.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from hauskraft_core.policy import PERMISSIONS
from hauskraft_sdk import DataClass, PluginContext
from hauskraft_sdk.tools import ToolSpec


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    spec: ToolSpec
    plugin_id: str
    context: PluginContext | None

    def wire(self) -> dict[str, Any]:
        """The Chat Completions function definition sent to models."""
        return {"name": self.spec.wire_name, "description": self.spec.description, "parameters": self.spec.parameters()}


class ToolRegistry:
    def __init__(self, tools: Iterable[RegisteredTool], guidance: dict[str, str] | None = None) -> None:
        self.guidance = dict(guidance or {})  # plugin id -> contributes.agent_guidance
        agent_tools = [t for t in tools if t.spec.agent]
        self._tools = sorted(agent_tools, key=lambda t: (t.plugin_id, t.spec.name))
        self._by_wire = {t.spec.wire_name: t for t in self._tools}
        self._by_name = {t.spec.name: t for t in self._tools}

    @classmethod
    def from_plugins(cls, plugins: dict[str, Any]) -> ToolRegistry:
        """Build from the loader's ``app.state.plugins``."""
        loaded = [p for p in plugins.values() if p.registration is not None]
        return cls(
            (
                RegisteredTool(spec, plugin.id, plugin.context)
                for plugin in loaded
                for spec in plugin.registration.tools
            ),
            guidance={
                p.id: text for p in loaded if (text := (p.manifest.get("contributes") or {}).get("agent_guidance"))
            },
        )

    def all(self) -> list[RegisteredTool]:
        return list(self._tools)

    def names(self) -> set[str]:
        return set(self._by_name)

    def by_wire_name(self, wire_name: str) -> RegisteredTool:
        return self._by_wire[wire_name]

    def by_name(self, name: str) -> RegisteredTool:
        return self._by_name[name]

    def select(
        self,
        *,
        role: str,
        disabled_tools: Iterable[str] = (),
        disabled_plugins: Iterable[str] = (),
        max_data_class: DataClass | str = DataClass.HOUSEHOLD,
        skill_tools: Sequence[str] | None = None,
    ) -> list[RegisteredTool]:
        off = set(disabled_tools)
        off_plugins = set(disabled_plugins)
        ceiling = DataClass(max_data_class)
        allowed = set(skill_tools) if skill_tools is not None else None
        return [
            t
            for t in self._tools
            if role in PERMISSIONS.get(t.spec.permission, frozenset())
            and t.spec.name not in off
            and t.plugin_id not in off_plugins
            and DataClass(t.spec.data_class) <= ceiling
            and (allowed is None or t.spec.name in allowed)
        ]


def tools_hash(tools: Sequence[RegisteredTool]) -> str:
    """A short fingerprint of the tool definitions a run offered, stored on runs and eval reports."""
    payload = json.dumps([t.wire() for t in tools], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
