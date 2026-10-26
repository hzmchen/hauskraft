# SPDX-License-Identifier: MIT
"""M2S-E09-01: datasets load and validate without a model (`just eval --check`), skill eval files are found."""

from pathlib import Path

import pytest

from hauskraft_evals.checks import language_of
from hauskraft_evals.datasets import Catalog, DatasetError, discover, load_dataset

pytestmark = pytest.mark.unit
REPO = Path(__file__).resolve().parents[2]
CATALOG = Catalog(tools={"tasks.list", "tasks.create", "tasks.delete"}, skills={"tasks.add-from-text"})

MINIMAL = """
name: demo
threshold: 0.9
cases:
  - name: add milk
    fixture: {tasks: [], today: 2026-11-02, timezone: Europe/Berlin, language: en}
    input: {message: "Add 'Buy milk'"}
    expect:
      tool_calls: [{name: tasks.create, args: {title: Buy milk}}]
      state: {exists: [Buy milk]}
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "demo.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_a_minimal_dataset_loads_with_defaults(tmp_path: Path) -> None:
    ds = load_dataset(_write(tmp_path, MINIMAL), CATALOG)
    assert ds.name == "demo"
    assert ds.repeat == 3
    case = ds.cases[0]
    assert case.fixture.role == "owner"
    assert case.expect.tool_calls is not None
    assert case.expect.tool_calls[0].args == {"title": "Buy milk"}


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("state: {exists: [Buy milk]}", "states: {}", "states"),
        ("name: tasks.create", "name: tasks.rename", "unknown tool"),
        ("state: {exists: [Buy milk]}", "answer_contains: ['(unclosed']", "regular expression"),
        ("input: {message: \"Add 'Buy milk'\"}", "input: {skill: tasks.nope}", "unknown skill"),
        ("input: {message: \"Add 'Buy milk'\"}", "input: {}", "message or a skill"),
        ("threshold: 0.9", "threshold: 1.5", "threshold"),
    ],
)
def test_invalid_datasets_are_refused(tmp_path: Path, old: str, new: str, message: str) -> None:
    assert old in MINIMAL
    with pytest.raises(DatasetError, match=message):
        load_dataset(_write(tmp_path, MINIMAL.replace(old, new)), CATALOG)


def test_case_names_are_unique(tmp_path: Path) -> None:
    doubled = MINIMAL + MINIMAL[MINIMAL.index("  - name") :]
    with pytest.raises(DatasetError, match="unique"):
        load_dataset(_write(tmp_path, doubled), CATALOG)


def test_skill_eval_files_are_discovered_and_run_with_their_skill() -> None:
    datasets = discover(REPO)
    for skill in ("tasks.add-from-text", "tasks.weekly-overview"):
        assert skill in datasets, sorted(datasets)
        assert all(case.input.skill == skill for case in datasets[skill].cases)


def test_every_dataset_in_the_repository_passes_the_check() -> None:
    # discover() validates each file against the plugins' tools and skills and raises on the first problem.
    assert discover(REPO)


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("I added 'Buy milk' for tomorrow. You have two open tasks.", "en"),
        ("Ich habe 'Buy milk' für morgen hinzugefügt. Du hast zwei offene Aufgaben.", "de"),
        ("'Milch kaufen'", None),
    ],
)
def test_the_answer_language_is_told_from_common_words(text: str, language: str | None) -> None:
    assert language_of(text) == language
