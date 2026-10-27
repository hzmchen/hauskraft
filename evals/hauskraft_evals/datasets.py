# SPDX-License-Identifier: MIT
"""Eval datasets: the YAML files in ``evals/datasets/`` and the ones plugin skills bring (ADR 0022).

The layout is the contract in ``docs/backlog/m2-star/E09-evals.md``. A skill's eval file (``evals:`` in its
``SKILL.md``) has the same format; its cases run that skill unless they say otherwise, and its name defaults to the
skill id.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Self

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from hauskraft_core.assistant.skills import parse as parse_skill

DATASETS = Path("evals") / "datasets"


class DatasetError(ValueError):
    """A dataset that can't run: its file, and what is wrong."""


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FixtureTask(_Model):
    title: str = Field(min_length=1, max_length=200)
    done: bool = False
    due_on: dt.date | None = None


class Fixture(_Model):
    """The household a case starts from: its tasks, the date and time zone, and the person's language and role."""

    tasks: list[FixtureTask]
    today: dt.date
    timezone: str
    language: Literal["en", "de"]
    time: dt.time = dt.time(9, 0)
    role: Literal["owner", "adult"] = "owner"


class CaseInput(_Model):
    """A chat ``message`` (optionally answering the confirmation it pauses for), or a ``skill`` with its ``text``."""

    message: str | None = Field(default=None, min_length=1)
    confirm: Literal["approved", "denied"] | None = None
    skill: str | None = None
    text: str | None = None

    @model_validator(mode="after")
    def _one_kind(self) -> Self:
        if (self.message is None) == (self.skill is None):
            raise ValueError("an input is either a message or a skill")
        if self.message is not None and self.text is not None:
            raise ValueError("text belongs to a skill input")
        if self.skill is not None and self.confirm is not None:
            raise ValueError("confirm belongs to a message input")
        return self


class ExpectedCall(_Model):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class ExpectedState(_Model):
    """Tasks (by title, ignoring case) that must exist, must not, must be done or open; and their total."""

    exists: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    done: list[str] = Field(default_factory=list)
    open: list[str] = Field(default_factory=list)
    count: int | None = Field(default=None, ge=0)


class Expect(_Model):
    tool_calls: list[ExpectedCall] | None = None
    no_tool_calls: list[str] | None = None
    paused_for_confirmation: bool | None = None
    state: ExpectedState | None = None
    answer_language: Literal["en", "de"] | None = None
    answer_contains: list[str] | None = None
    judge: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _something(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("a case expects something")
        for pattern in self.answer_contains or []:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"answer_contains {pattern!r} is not a regular expression: {exc}") from exc
        return self


class EvalCase(_Model):
    name: str = Field(min_length=1)
    fixture: Fixture
    input: CaseInput
    expect: Expect


class EvalDataset(_Model):
    name: str = Field(min_length=1)
    description: str | None = None
    threshold: float = Field(ge=0, le=1)
    repeat: int = Field(default=3, ge=1, le=10)
    cases: list[EvalCase] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_names(self) -> Self:
        names = [c.name for c in self.cases]
        if len(set(names)) != len(names):
            raise ValueError("case names must be unique")
        return self


@dataclass(frozen=True)
class Catalog:
    """The tool names and skill ids the plugins declare, to check datasets without starting the app."""

    tools: set[str]
    skills: set[str]


@dataclass(frozen=True)
class SkillEvals:
    skill: str
    path: Path


def _manifests(repo: Path) -> list[tuple[Path, dict[str, Any]]]:
    found = []
    for path in sorted((repo / "plugins").glob("*/*/hauskraft.plugin.json")):
        found.append((path.parent, json.loads(path.read_text(encoding="utf-8"))))
    return found


def catalog(repo: Path) -> tuple[Catalog, list[SkillEvals]]:
    """Read every plugin manifest for its tools, its skills and the eval files those skills reference."""
    tools: set[str] = set()
    skills: set[str] = set()
    evals: list[SkillEvals] = []
    for folder, manifest in _manifests(repo):
        contributes = manifest.get("contributes") or {}
        tools |= {t["name"] for t in contributes.get("tools") or [] if t.get("agent", True)}
        short = str(manifest["id"]).rsplit(".", 1)[-1]
        for entry in contributes.get("skills") or []:
            skill_id = f"{short}.{entry['id']}"
            skills.add(skill_id)
            skill_file = folder / entry["path"]
            meta, _ = parse_skill(skill_file)
            if meta.get("evals"):
                evals.append(SkillEvals(skill_id, skill_file.parent / str(meta["evals"])))
    return Catalog(tools, skills), evals


def _check(ds: EvalDataset, known: Catalog) -> None:
    for case in ds.cases:
        where = f"case {case.name!r}"
        named = [c.name for c in case.expect.tool_calls or []] + [
            n for n in case.expect.no_tool_calls or [] if n != "*"
        ]
        unknown = sorted(set(named) - known.tools)
        if unknown:
            raise ValueError(f"{where}: unknown tool {', '.join(unknown)}")
        if case.input.skill is not None and case.input.skill not in known.skills:
            raise ValueError(f"{where}: unknown skill {case.input.skill}")


def load_dataset(path: Path, known: Catalog, *, skill: str | None = None) -> EvalDataset:
    """Load and check one dataset; ``skill`` fills in the skill and the name of a skill's own eval file."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if skill is not None:
            raw.setdefault("name", skill)
            for case in raw.get("cases") or []:
                inp = case.setdefault("input", {})
                if "message" not in inp:
                    inp.setdefault("skill", skill)
        ds = EvalDataset.model_validate(raw)
        _check(ds, known)
    except (OSError, yaml.YAMLError, ValidationError, ValueError) as exc:
        raise DatasetError(f"{path}: {exc}") from exc
    return ds


def discover(repo: Path) -> dict[str, EvalDataset]:
    """Every dataset: ``evals/datasets/*.yaml`` and the eval files of plugin skills, checked, by name."""
    known, skill_evals = catalog(repo)
    found: dict[str, EvalDataset] = {}
    sources = [(p, None) for p in sorted((repo / DATASETS).glob("*.yaml"))] + [(s.path, s.skill) for s in skill_evals]
    for path, skill in sources:
        ds = load_dataset(path, known, skill=skill)
        if ds.name in found:
            raise DatasetError(f"{path}: a second dataset named {ds.name!r}")
        found[ds.name] = ds
    return found
