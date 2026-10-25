# SPDX-License-Identifier: MIT
"""M2S-E01 static checks: the fake model in the test stack and CI wiring (ADR 0022)."""

from __future__ import annotations

import re
from typing import Any

import pytest
import yaml

from _support.red import require_text

story = pytest.mark.story


class _ComposeLoader(yaml.SafeLoader):
    """Compose files may use `!reset` / `!override`; keep the tagged value and drop the tag."""


def _tagged(loader: yaml.SafeLoader, _suffix: str, node: yaml.Node) -> Any:
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return loader.construct_scalar(node)


_ComposeLoader.add_multi_constructor("!", _tagged)


def _yaml(rel: str, sid: str) -> dict:
    return yaml.load(require_text(rel, sid), Loader=_ComposeLoader) or {}  # noqa: S506 - safe subclass


# ---------------------------------------------------------------- M2S-E01-01
@story("M2S-E01-01")
def test_test_overlay_runs_the_fake_model() -> None:
    services = _yaml("deploy/compose/compose.test.yaml", "M2S-E01-01").get("services", {})
    fake = services.get("fake-llm")
    assert fake, "RED: deploy/compose/compose.test.yaml has no fake-llm service"
    assert str(fake.get("image", "")).startswith("python:3.13"), "standard library only: a plain Python image"
    mounts = " ".join(str(v) for v in fake.get("volumes", []))
    assert "tests/fixtures/fake-llm" in mounts and ":ro" in mounts, "the spec-owned fixture, mounted read-only"
    assert "server.py" in str(fake.get("command", "")) + str(fake.get("entrypoint", ""))
    ports = [str(p) for p in fake.get("ports", [])]
    assert ports and all(p.startswith("127.0.0.1:8090:") for p in ports), "reachable from this machine only"
    assert "healthcheck" in fake


@story("M2S-E01-01")
def test_production_compose_has_no_fake_model() -> None:
    assert "fake-llm" not in _yaml("compose.yaml", "M2S-E01-01").get("services", {})


@story("M2S-E01-01")
def test_justfile_can_reset_the_fake_model() -> None:
    text = require_text("justfile", "M2S-E01-01")
    m = re.search(r"^fake-llm-reset\b.*?:\n((?:[ \t]+.*\n?)+)", text, re.M)
    assert m, "RED: no `fake-llm-reset` recipe in the justfile"
    assert "/_reset" in m.group(1)


# ---------------------------------------------------------------- M2S-E01-02
@story("M2S-E01-02")
def test_e2e_workflow_points_the_tests_at_the_fake_model() -> None:
    text = require_text(".github/workflows/e2e.yml", "M2S-E01-02")
    assert re.search(r"HAUSKRAFT_FAKE_LLM_URL:\s*http://fake-llm:8090/v1", text)
    assert re.search(r"HAUSKRAFT_FAKE_LLM_ADMIN_URL:\s*http://localhost:8090", text)


@story("M2S-E01-02")
@pytest.mark.parametrize("rel", [".github/workflows/ci.yml", ".github/workflows/e2e.yml"])
def test_everyday_ci_needs_no_provider_secret(rel: str) -> None:
    text = require_text(rel, "M2S-E01-02")
    secrets = set(re.findall(r"secrets\.([A-Z0-9_]+)", text)) - {"GITHUB_TOKEN"}
    assert not {s for s in secrets if "EVAL" in s or "OPENAI" in s or "LLM" in s}, secrets
