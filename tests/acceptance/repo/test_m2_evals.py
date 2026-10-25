# SPDX-License-Identifier: MIT
"""M2S-E09 static checks: eval layout, datasets, commands and the on-demand workflow (ADR 0022)."""

from __future__ import annotations

import re

import pytest
import yaml

from _support import REPO
from _support.red import require_file, require_text

story = pytest.mark.story
DATASETS = {"chat-tasks": 10, "add-from-text": 8, "weekly-overview": 5, "safety": 6}
EXPECT_KEYS = {"tool_calls", "no_tool_calls", "paused_for_confirmation", "state", "answer_language", "answer_contains",
               "judge"}


def _dataset(name: str, sid: str) -> dict:
    return yaml.safe_load(require_text(f"evals/datasets/{name}.yaml", sid)) or {}


# ---------------------------------------------------------------- M2S-E09-01
@story("M2S-E09-01")
def test_eval_readme_and_commands_exist() -> None:
    readme = require_text("evals/README.md", "M2S-E09-01")
    for word in ("HAUSKRAFT_EVAL_BASE_URL", "HAUSKRAFT_EVAL_API_KEY", "HAUSKRAFT_EVAL_MODEL", "just eval", "cost"):
        assert word in readme, f"evals/README.md should mention {word!r}"
    justfile = require_text("justfile", "M2S-E09-01")
    for recipe in ("eval", "eval-compare"):
        assert re.search(rf"^{recipe}\b[^:\n]*:", justfile, re.M), f"no `{recipe}` recipe in the justfile"


@story("M2S-E09-01")
def test_reports_are_not_committed() -> None:
    ignored = require_text(".gitignore", "M2S-E09-01")
    assert re.search(r"(?m)^/?evals/reports/?", ignored), "evals/reports/ belongs in .gitignore"


@story("M2S-E09-01")
def test_pydantic_evals_is_a_development_dependency() -> None:
    lock = require_text("uv.lock", "M2S-E09-01")
    assert 'name = "pydantic-evals"' in lock


# ---------------------------------------------------------------- M2S-E09-02
@story("M2S-E09-02")
@pytest.mark.parametrize(("name", "minimum"), DATASETS.items())
def test_dataset_shape(name: str, minimum: int) -> None:
    ds = _dataset(name, "M2S-E09-02")
    assert ds.get("name") == name
    threshold = ds.get("threshold")
    assert threshold == 1.0 if name == "safety" else (isinstance(threshold, float) and threshold >= 0.9)
    assert int(ds.get("repeat", 3)) >= 1
    cases = ds.get("cases") or []
    assert len(cases) >= minimum, f"{name} needs at least {minimum} cases"
    names = [c.get("name") for c in cases]
    assert all(names) and len(set(names)) == len(names), "every case has a unique name"
    for case in cases:
        assert set(case.get("fixture", {})) >= {"tasks", "today", "timezone", "language"}, case.get("name")
        assert "message" in case.get("input", {}) or "skill" in case.get("input", {}), case.get("name")
        expect = case.get("expect") or {}
        assert expect and set(expect) <= EXPECT_KEYS, (case.get("name"), set(expect) - EXPECT_KEYS)
        if "judge" in expect:
            assert name == "weekly-overview", "LLM judges only for the overview's quality"


@story("M2S-E09-02")
def test_add_from_text_has_injection_cases() -> None:
    cases = _dataset("add-from-text", "M2S-E09-02").get("cases", [])
    injected = [c for c in cases if re.search(r"(?i)ignore|instruction|delete all", str(c.get("input", {}).get("text")))]
    assert len(injected) >= 3, "at least three prompt-injection cases"
    assert all("no_tool_calls" in c["expect"] or "state" in c["expect"] for c in injected)


@story("M2S-E09-02")
def test_safety_covers_the_rules() -> None:
    cases = _dataset("safety", "M2S-E09-02").get("cases", [])
    flat = yaml.safe_dump(cases)
    assert any("paused_for_confirmation" in c.get("expect", {}) for c in cases), "a delete pauses"
    assert re.search(r"(?i)denied", flat), "a denied confirmation changes nothing"
    assert re.search(r"(?i)adult", flat), "an adult can't reach owner-only tools"
    assert re.search(r"(?i)ignore|instruction", flat), "injected instructions cause no tool call"


@story("M2S-E09-02")
def test_a_real_model_run_is_summarised() -> None:
    readme = require_text("evals/README.md", "M2S-E09-02")
    assert re.search(r"(?im)^#+ .*results", readme), "evals/README.md summarises the first real-model run"
    assert re.search(r"prompt_version|prompt version", readme)


# ---------------------------------------------------------------- M2S-E09-03
@story("M2S-E09-03")
def test_eval_workflow_runs_only_on_demand() -> None:
    doc = yaml.safe_load(require_text(".github/workflows/evals.yml", "M2S-E09-03"))
    triggers = doc.get(True) or doc.get("on")  # YAML 1.1 reads `on` as True
    assert set(triggers) == {"workflow_dispatch"}, triggers
    text = require_file(".github/workflows/evals.yml", "M2S-E09-03").read_text(encoding="utf-8")
    assert "secrets.HAUSKRAFT_EVAL_API_KEY" in text
    assert "upload-artifact" in text


@story("M2S-E09-03")
def test_ci_recommends_evals_without_secrets() -> None:
    text = require_text(".github/workflows/ci.yml", "M2S-E09-03")
    assert "Eval recommended" in text
    for path in ("assistant/prompts", "skills", "evals/datasets", "tools.py"):
        assert path in text, f"the eval-recommended check should watch {path}"


@story("M2S-E09-03")
def test_pr_template_asks_about_evals() -> None:
    text = (REPO / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    assert re.search(r"(?i)eval", text)
