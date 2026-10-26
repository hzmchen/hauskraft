# SPDX-License-Identifier: AGPL-3.0-or-later
"""Skills (M2S-E05-01, ADR 0023): ``SKILL.md`` bundles contributed by plugins.

At startup every ``contributes.skills[]`` entry is read from the plugin's folder, its YAML frontmatter validated
against ``packages/schemas/skill/skill.schema.json`` and its tools checked against the registry. A broken skill is
left out and recorded as the plugin's load error. The global id is ``<plugin short name>.<id>``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from hauskraft_core import schemas
from hauskraft_core.logging import get_logger

SCHEMA = "skill/skill.schema.json"
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.S)

_log = get_logger("hauskraft.assistant")


@dataclass(frozen=True, slots=True)
class Skill:
    id: str
    plugin_id: str
    name: str
    description: str
    tools: tuple[str, ...]
    output: str | dict[str, Any]  # "text" or a JSON schema
    instructions: str

    @property
    def output_kind(self) -> str:
        return "text" if self.output == "text" else "json"


class SkillError(ValueError):
    pass


def parse(path: Path) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if not match:
        raise SkillError(f"{path.name}: no YAML frontmatter")
    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        raise SkillError(f"{path.name}: the frontmatter is not a mapping")
    return meta, match.group(2).strip()


def load_skill(plugin_id: str, folder: Path, entry: dict[str, Any], tool_names: set[str]) -> Skill:
    path = (folder / str(entry["path"])).resolve()
    if folder.resolve() not in path.parents:
        raise SkillError(f"{entry['path']}: outside the plugin")
    if not path.is_file():
        raise SkillError(f"{entry['path']}: not found")
    meta, body = parse(path)
    problems = schemas.errors(SCHEMA, meta)
    if problems:
        raise SkillError(f"{entry['path']}: " + "; ".join(problems[:3]))
    unknown = sorted(set(meta["tools"]) - tool_names)
    if unknown:
        raise SkillError(f"{entry['path']}: unknown tools {', '.join(unknown)}")
    if not body:
        raise SkillError(f"{entry['path']}: no instructions")
    output = meta["output"] if meta["output"] == "text" else meta["output"]["schema"]
    return Skill(
        id=f"{plugin_id.rsplit('.', 1)[-1]}.{entry['id']}",
        plugin_id=plugin_id,
        name=meta["name"],
        description=meta["description"],
        tools=tuple(meta["tools"]),
        output=output,
        instructions=body,
    )


def load_skills(plugins: dict[str, Any], tool_names: set[str], load_errors: dict[str, str]) -> dict[str, Skill]:
    skills: dict[str, Skill] = {}
    for plugin in plugins.values():
        if plugin.registration is None:
            continue
        for entry in (plugin.manifest.get("contributes") or {}).get("skills") or []:
            try:
                skill = load_skill(plugin.id, plugin.folder, entry, tool_names)
            except (SkillError, OSError, yaml.YAMLError) as exc:
                plugin.load_error = f"skill {entry.get('id')}: {exc}"
                load_errors[plugin.id] = plugin.load_error
                _log.warning("skill.invalid", plugin_id=plugin.id, error=str(exc))
                continue
            skills[skill.id] = skill
    return skills
