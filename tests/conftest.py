# SPDX-License-Identifier: MIT
"""Story-aware red/green plumbing for the Hauskraft acceptance suite.

Every test carries ``@pytest.mark.story("M0S-Exx-yy", ...)`` (or ``@pytest.mark.meta``).
tests/story-status.json says whether each story is red or green:

* green story  -> its tests are hard gates (must pass).
* red story    -> its tests run but are reported as xfail ("RED: ...") so the suite stays
                  usable while work is in progress. Unexpected passes show as XPASS.

Options:
  --story ID     run only tests for these stories, in raw mode (real failures shown).
                 This is the TDD loop for an agent working on one story.
  --raw          disable the red -> xfail mapping for all tests.
  --live         also run tests that need a running stack (HAUSKRAFT_BASE_URL).
  --strict-status  fail the run if a red story has every one of its tests passing,
                 i.e. the story is green and tests/story-status.json must be flipped.
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _support import stories as story_registry  # noqa: E402

_RESULTS: dict[str, dict[str, int]] = defaultdict(lambda: {"passed": 0, "failed": 0})
_COLLECTED: dict[str, int] = defaultdict(int)  # every test of a story, before --story/--live filtering


def pytest_addoption(parser: pytest.Parser) -> None:
    g = parser.getgroup("hauskraft")
    g.addoption("--story", action="append", default=[], metavar="ID",
                help="Run only tests for these story IDs, without red->xfail mapping.")
    g.addoption("--raw", action="store_true", help="Do not map red stories to xfail.")
    g.addoption("--live", action="store_true",
                help="Run live tests against a running stack (HAUSKRAFT_BASE_URL).")
    g.addoption("--strict-status", action="store_true",
                help="Fail if a red story has all of its tests passing.")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "story(*ids): links a test to backlog story IDs")
    config.addinivalue_line("markers", "live: needs a running Hauskraft stack (use --live)")
    config.addinivalue_line("markers", "meta: validates the docs and the suite itself")


def _story_ids(item: pytest.Item) -> list[str]:
    ids: list[str] = []
    for mark in item.iter_markers("story"):
        ids.extend(mark.args)
    return sorted(set(ids))


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    registry = story_registry.load()
    wanted = set(config.getoption("--story"))
    raw = config.getoption("--raw") or bool(wanted)
    live = config.getoption("--live") or os.environ.get("HAUSKRAFT_LIVE") == "1"
    unknown_wanted = wanted - registry.keys()
    if unknown_wanted:
        raise pytest.UsageError(f"Unknown story id(s): {', '.join(sorted(unknown_wanted))}")

    selected, deselected = [], []
    for item in items:
        ids = _story_ids(item)
        is_meta = item.get_closest_marker("meta") is not None
        if not ids and not is_meta:
            raise pytest.UsageError(
                f"{item.nodeid}: every test needs @pytest.mark.story(...) or @pytest.mark.meta")
        unknown = [i for i in ids if i not in registry]
        if unknown:
            raise pytest.UsageError(f"{item.nodeid}: unknown story id(s) {unknown}")
        for sid in ids:
            _COLLECTED[sid] += 1
        if wanted and not (set(ids) & wanted):
            deselected.append(item)
            continue
        if item.get_closest_marker("live") and not live:
            item.add_marker(pytest.mark.skip(
                reason="live test: start the stack, then run with --live (see tests/README.md)"))
        red = [i for i in ids if registry[i]["status"] == "red"]
        if red and not raw:
            item.add_marker(pytest.mark.xfail(
                reason=f"RED: {', '.join(red)} not implemented yet", strict=False))
        item.user_properties.append(("stories", ids))
        selected.append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    ids = dict(report.user_properties).get("stories") or []
    if not ids:
        return
    failed = report.failed or (hasattr(report, "wasxfail") and report.skipped)
    passed = report.when == "call" and report.passed
    for sid in ids:
        if failed:
            _RESULTS[sid]["failed"] += 1
        elif passed:
            _RESULTS[sid]["passed"] += 1


def _ready_to_flip() -> list[str]:
    """Red stories whose every collected test ran and passed (none skipped, deselected or failed)."""
    registry = story_registry.load()
    return sorted(
        sid for sid, r in _RESULTS.items()
        if registry[sid]["status"] == "red" and r["failed"] == 0 and r["passed"] == _COLLECTED[sid] > 0
    )


def _green_failing() -> list[str]:
    registry = story_registry.load()
    return sorted(sid for sid, r in _RESULTS.items()
                  if registry[sid]["status"] == "green" and r["failed"] > 0)


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:  # type: ignore[no-untyped-def]
    flip, broken = _ready_to_flip(), _green_failing()
    if not (flip or broken):
        return
    tr = terminalreporter
    tr.section("Hauskraft story status")
    for sid in flip:
        tr.write_line(f"READY  {sid}: all its tests pass. Set it to \"green\" in tests/story-status.json.")
    for sid in broken:
        tr.write_line(f"BROKEN {sid}: marked green but tests fail.")


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if session.config.getoption("--strict-status") and _ready_to_flip() and exitstatus == 0:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
