# SPDX-License-Identifier: MIT
"""E02 · CI & quality gates. Workflow shape plus the denylist and licence-map scripts."""

from __future__ import annotations

import pytest

from _support import FIXTURES, REPO
from _support.files import yaml_doc
from _support.red import require_text
from _support.tools import node_script, python_script

story = pytest.mark.story


def _jobs(rel: str, sid: str) -> dict:
    doc = yaml_doc(rel, sid) or {}
    return doc.get("jobs", {})


def _triggers(rel: str, sid: str) -> dict:
    doc = yaml_doc(rel, sid) or {}
    # PyYAML reads the bare key `on` as boolean True.
    return doc.get("on", doc.get(True, {})) or {}


# ---------------------------------------------------------------- M0S-E02-01
@story("M0S-E02-01")
def test_ci_has_fast_parallel_jobs() -> None:
    jobs = _jobs(".github/workflows/ci.yml", "M0S-E02-01")
    for job in ("lint", "typecheck", "unit-py", "unit-web", "acceptance"):
        assert job in jobs, f"ci.yml lacks job {job!r}: {sorted(jobs)}"
    assert "pull_request" in _triggers(".github/workflows/ci.yml", "M0S-E02-01")


@story("M0S-E02-01")
def test_ci_cancels_superseded_runs() -> None:
    doc = yaml_doc(".github/workflows/ci.yml", "M0S-E02-01") or {}
    assert (doc.get("concurrency") or {}).get("cancel-in-progress") is True


@story("M0S-E02-01")
def test_ci_runs_acceptance_suite_with_strict_status() -> None:
    text = require_text(".github/workflows/ci.yml", "M0S-E02-01")
    assert "pytest" in text and "tests" in text and "--strict-status" in text, \
        "the acceptance job must run `python -m pytest tests --strict-status`"


# ---------------------------------------------------------------- M0S-E02-02
@story("M0S-E02-02")
def test_ci_has_contract_job() -> None:
    jobs = _jobs(".github/workflows/ci.yml", "M0S-E02-02")
    assert "contract" in jobs
    text = require_text(".github/workflows/ci.yml", "M0S-E02-02")
    assert "integration or contract" in text
    assert "git diff --exit-code" in text, "drift of generated artefacts must fail CI"


# ---------------------------------------------------------------- M0S-E02-03
@story("M0S-E02-03")
def test_e2e_workflow_runs_stack_and_suites() -> None:
    text = require_text(".github/workflows/e2e.yml", "M0S-E02-03")
    assert "docker compose" in text and "up --wait" in text
    assert "compose.test.yaml" in text, "the e2e stack must include the test overlay with fixture themes"
    assert "--live" in text, "live API acceptance tests must run in the e2e job"
    assert "playwright test" in text
    assert "upload-artifact" in text and "failure()" in text, "upload traces/reports on failure"


# ---------------------------------------------------------------- M0S-E02-04
@story("M0S-E02-04")
def test_dco_is_enforced() -> None:
    wf = REPO / ".github" / "workflows"
    texts = [p.read_text().lower() for p in wf.glob("*.y*ml")] if wf.exists() else []
    assert (REPO / ".github" / "dco.yml").exists() or any("dco" in t for t in texts), \
        "RED (M0S-E02-04): no DCO check configured"


@story("M0S-E02-04")
def test_licence_map_accepts_good_tree() -> None:
    proc = python_script("scripts/check-licence-map.py", "--root", str(FIXTURES / "licence-map" / "good"),
                         story="M0S-E02-04")
    assert proc.returncode == 0, proc.stdout + proc.stderr


@story("M0S-E02-04")
def test_licence_map_rejects_bad_tree() -> None:
    proc = python_script("scripts/check-licence-map.py", "--root", str(FIXTURES / "licence-map" / "bad"),
                         story="M0S-E02-04")
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "packages/sdk-py/sdk.py" in out and "services/core_api/app.py" in out, out


# ---------------------------------------------------------------- M0S-E02-05
@story("M0S-E02-05")
def test_dependabot_ecosystems() -> None:
    doc = yaml_doc(".github/dependabot.yml", "M0S-E02-05") or {}
    eco = {u.get("package-ecosystem") for u in doc.get("updates", [])}
    assert {"npm", "github-actions", "docker"} <= eco, eco
    assert eco & {"uv", "pip"}, f"python dependencies not covered: {eco}"


@story("M0S-E02-05")
def test_denylist_accepts_clean_lockfile() -> None:
    proc = node_script("scripts/check-denylist.mjs", str(FIXTURES / "lockfiles" / "clean-pnpm-lock.yaml"),
                       story="M0S-E02-05")
    assert proc.returncode == 0, proc.stdout + proc.stderr


@story("M0S-E02-05")
def test_denylist_rejects_compromised_lockfile() -> None:
    proc = node_script("scripts/check-denylist.mjs", str(FIXTURES / "lockfiles" / "compromised-pnpm-lock.yaml"),
                       story="M0S-E02-05")
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "1.169.5" in out and "1.167.41" in out, out
