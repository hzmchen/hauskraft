# SPDX-License-Identifier: MIT
"""M0S-E02-01: ci.yml jobs install what they need and stay independent (they run in parallel)."""

from __future__ import annotations

import pytest
import yaml
from _support import REPO

pytestmark = pytest.mark.story("M0S-E02-01")

CI = REPO / ".github" / "workflows" / "ci.yml"


def _ci() -> dict:
    assert CI.exists(), "ci.yml missing"
    return yaml.safe_load(CI.read_text())


def test_jobs_run_in_parallel() -> None:
    for name in ("lint", "typecheck", "unit-py", "unit-web", "acceptance"):
        assert "needs" not in _ci()["jobs"][name], f"{name} must not wait for another job"


def test_every_job_has_a_timeout_under_eight_minutes() -> None:
    for name, job in _ci()["jobs"].items():
        assert 0 < job.get("timeout-minutes", 0) <= 8, f"{name}: timeout-minutes must be set and <= 8"


def test_actions_are_pinned_to_exact_versions() -> None:
    texts = [CI.read_text(), (REPO / ".github" / "actions" / "setup" / "action.yml").read_text()]
    for line in "\n".join(texts).splitlines():
        if "uses:" in line and "@" in line:  # local actions (./.github/actions/...) have no ref
            ref = line.split("@", 1)[1].split()[0]
            assert ref.count(".") >= 2 or len(ref) == 40, f"pin {line.strip()!r} to an exact release or SHA"


def test_bootstrap_workflow_is_gone() -> None:
    assert not (REPO / ".github" / "workflows" / "acceptance.yml").exists(), "ci.yml replaces acceptance.yml"
