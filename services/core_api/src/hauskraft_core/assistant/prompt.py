# SPDX-License-Identifier: AGPL-3.0-or-later
"""The system prompt (M2S-E04-03, spec §8.0).

Short English template files, assembled in a fixed order with the stable parts first, so providers can cache the
prefix: role, rules, style for the channel, the offered plugins' guidance, the running skill's instructions, and the
context block last (date and time in the household time zone, household, person, language, skill). The
``prompt_version`` is a hash of the template files; every run and every eval report stores it.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from zoneinfo import ZoneInfo

PROMPTS = Path(__file__).with_name("prompts")
LANGUAGES = {"en": "English", "de": "German"}
CHANNELS = ("text", "voice")


@dataclass(frozen=True)
class PromptContext:
    now: dt.datetime
    timezone: str
    household: str
    person: str
    role: str
    locale: str


@cache
def _template(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8").strip()


@cache
def prompt_version() -> str:
    digest = hashlib.sha256()
    for path in sorted(PROMPTS.glob("*.md")):
        digest.update(path.name.encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()[:12]


def context_block(ctx: PromptContext, skill_id: str | None = None) -> str:
    local = ctx.now.astimezone(ZoneInfo(ctx.timezone))
    block = _template("context.md").format(
        date=local.date().isoformat(),
        weekday=local.strftime("%A"),
        time=local.strftime("%H:%M"),
        timezone=ctx.timezone,
        household=ctx.household,
        person=ctx.person,
        role=ctx.role,
        language=LANGUAGES.get(ctx.locale, "English"),
    )
    return block + (f"\nSkill: {skill_id}" if skill_id else "")


def render(
    ctx: PromptContext,
    *,
    guidance: Sequence[str] = (),
    skill_id: str | None = None,
    skill_instructions: str | None = None,
    channel: str = "text",
) -> str:
    parts = [
        _template("role.md"),
        _template("rules.md"),
        _template(f"style.{channel if channel in CHANNELS else 'text'}.md"),
    ]
    if guidance:
        parts.append("Notes about the tools:\n" + "\n".join(f"- {g.strip()}" for g in guidance if g.strip()))
    if skill_instructions:
        parts.append("Your task:\n" + skill_instructions.strip())
    parts.append(context_block(ctx, skill_id))
    return "\n\n".join(parts) + "\n"
