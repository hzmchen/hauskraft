# SPDX-License-Identifier: AGPL-3.0-or-later
"""The gate (M2S-E04-04, ADR 0020): one function decides each tool call: allow, confirm or deny.

The M2* rule: a tool outside the run's selection is denied, a destructive tool needs the person's confirmation,
everything else is allowed. Callers store every decision with its reason, so confirmation rates can be measured
before a risk classifier ("auto mode"), schedules (confirm becomes an approval request) or voice change the rule.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from hauskraft_core.assistant.registry import RegisteredTool
from hauskraft_sdk import Actor

Decision = Literal["allow", "confirm", "deny"]


@dataclass(frozen=True, slots=True)
class GateContext:
    offered: frozenset[str]
    run_kind: Literal["interactive", "scheduled"] = "interactive"
    channel: Literal["text", "voice"] = "text"
    tainted: bool = False
    history: tuple[str, ...] = field(default=())


def decide(
    tool: RegisteredTool, args: Mapping[str, Any], actor: Actor, ctx: GateContext, *, approved: bool = False
) -> tuple[Decision, str]:
    if tool.spec.name not in ctx.offered:
        return "deny", "not offered to this run"
    if approved:
        return "allow", "confirmed by the person"
    if tool.spec.annotations.destructive:
        return "confirm", "destructive"
    return "allow", "read-only" if tool.spec.annotations.read_only else "reversible write"
