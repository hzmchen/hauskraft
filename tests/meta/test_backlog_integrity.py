# SPDX-License-Identifier: MIT
"""Validation of the docs themselves: backlog, spec cross-references, story status and coverage.

These tests carry no story: they must be green at all times.
"""

from __future__ import annotations

import importlib.util
import json
import sys

import pytest

from _support import REPO, STATUS_FILE

pytestmark = pytest.mark.meta

_spec = importlib.util.spec_from_file_location("backlog_tools", REPO / "scripts" / "backlog_tools.py")
bt = importlib.util.module_from_spec(_spec)
assert _spec.loader
sys.modules["backlog_tools"] = bt  # dataclasses need the module registered
_spec.loader.exec_module(bt)


@pytest.fixture(scope="module")
def stories():
    return bt.parse_stories()


def test_backlog_has_stories(stories) -> None:
    assert len(stories) >= 40


def test_every_story_has_required_fields_and_estimate(stories) -> None:
    problems = [p for p in bt.check() if "missing **" in p or "estimate" in p]
    assert not problems, problems


def test_dependencies_exist_and_are_acyclic(stories) -> None:
    unknown = [(s.id, d) for s in stories.values() for d in s.deps if d not in stories]
    assert not unknown, unknown
    assert not bt.find_cycles(stories)


def test_every_milestone_has_a_backlog() -> None:
    assert list(bt.backlogs()) == sorted(bt.backlogs(), key=lambda p: int(p[1:-1]))
    assert {"M0S", "M1S"} <= set(bt.backlogs())


@pytest.mark.parametrize("prefix", list(bt.backlogs()))
def test_readme_counts_match_epic_files(stories, prefix: str) -> None:
    mine = [sid for sid in stories if bt.prefix_of(sid) == prefix]
    per_epic, total = bt.readme_totals(bt.backlogs()[prefix])
    assert total == len(mine)
    for epic, n in per_epic.items():
        assert sum(1 for sid in mine if bt.epic_of(sid) == epic) == n, epic


def test_spec_section_references_resolve() -> None:
    problems = [p for p in bt.check() if "not found in the spec" in p]
    assert not problems, problems


def test_status_registry_matches_backlog(stories) -> None:
    status = json.loads(STATUS_FILE.read_text())["stories"]
    assert set(status) == set(stories)
    assert {v["status"] for v in status.values()} <= {"red", "green"}
    assert {v["acceptance"] for v in status.values()} <= {"suite", "in-story"}


def test_suite_stories_have_acceptance_tests() -> None:
    problems = [p for p in bt.check() if "no acceptance test" in p or "unknown story" in p]
    assert not problems, problems


def test_whole_check_is_clean() -> None:
    assert bt.check() == []


def test_traceability_doc_is_current() -> None:
    path = REPO / "docs" / "testing" / "traceability.md"
    assert path.exists(), "run: python scripts/backlog_tools.py coverage --write"
    assert path.read_text(encoding="utf-8") == bt.write_traceability(), \
        "docs/testing/traceability.md is stale: run python scripts/backlog_tools.py coverage --write"
