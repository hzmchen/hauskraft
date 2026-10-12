# SPDX-License-Identifier: MIT
"""E12 · Docs, ADRs & community files, licences."""

from __future__ import annotations

import re

import pytest

from _support import REPO
from _support.red import require_file, require_text

story = pytest.mark.story


# ---------------------------------------------------------------- M0S-E12-01
@story("M0S-E12-01")
def test_root_agents_md_is_short_and_linked() -> None:
    text = require_text("AGENTS.md", "M0S-E12-01")
    assert len(text.splitlines()) < 300
    for link in ("docs/spec/hearthos-spec-v0.2.md", "docs/backlog/m0-star/README.md", "docs/testing/README.md"):
        assert link in text, f"AGENTS.md should link {link}"
    assert re.search(r"red", text, re.I) and re.search(r"green", text, re.I), "AGENTS.md must describe red/green TDD"


@story("M0S-E12-01")
@pytest.mark.parametrize("folder", ["plugins/official/tasks", "apps/web", "packages/ui", "themes"])
def test_nested_agents_md(folder: str) -> None:
    require_file(f"{folder}/AGENTS.md", "M0S-E12-01")


# ---------------------------------------------------------------- M0S-E12-02
@story("M0S-E12-02")
def test_adr_index_exists() -> None:
    require_file("docs/adr/README.md", "M0S-E12-02")


@story("M0S-E12-02")
@pytest.mark.parametrize("number", range(1, 15))
def test_adr_present_and_accepted(number: int) -> None:
    matches = sorted((REPO / "docs" / "adr").glob(f"{number:04d}-*.md")) if (REPO / "docs" / "adr").exists() else []
    assert matches, f"RED (M0S-E12-02): ADR {number:04d} missing"
    assert re.search(r"status\W+accepted", matches[0].read_text(), re.I), f"{matches[0].name} is not Accepted"


@story("M0S-E12-02")
def test_adr_0013_fixes_theme_thresholds() -> None:
    matches = sorted((REPO / "docs" / "adr").glob("0013-*.md")) if (REPO / "docs" / "adr").exists() else []
    assert matches, "RED (M0S-E12-02): ADR 0013 missing"
    text = matches[0].read_text()
    for number in ("4.5", "3", "0.15", "2 MB", "10 MB"):
        assert number in text, f"ADR-0013 should state {number}"


# ---------------------------------------------------------------- M0S-E12-03
MIT_PACKAGES = ["packages/sdk-py", "packages/sdk-ts", "packages/ui", "packages/schemas",
                "plugins/official/tasks", "themes/template", "integrations/ha-hearthos"]


@story("M0S-E12-03")
def test_root_licence_is_agpl() -> None:
    assert require_text("LICENSE", "M0S-E12-03").lstrip().startswith("GNU AFFERO GENERAL PUBLIC LICENSE")


@story("M0S-E12-03")
@pytest.mark.parametrize("folder", MIT_PACKAGES)
def test_plugin_facing_package_is_mit(folder: str) -> None:
    text = require_text(f"{folder}/LICENSE", "M0S-E12-03")
    assert text.lstrip().startswith("MIT License"), f"{folder}/LICENSE must be MIT"


@story("M0S-E12-03", "M0S-E13-06")
@pytest.mark.parametrize("theme", ["default", "paper", "hackspace"])
def test_builtin_theme_is_mit(theme: str) -> None:
    text = require_text(f"themes/builtin/{theme}/LICENSE", "M0S-E13-06")
    assert text.lstrip().startswith("MIT License")


@story("M0S-E12-03")
def test_licensing_md_explains_split() -> None:
    text = require_text("LICENSING.md", "M0S-E12-03")
    for needle in ("AGPL-3.0-or-later", "MIT", "OFL-1.1", "in-process", "not legal advice"):
        assert needle.lower() in text.lower(), f"LICENSING.md should mention {needle!r}"


@story("M0S-E12-03")
def test_reuse_toml_exists() -> None:
    require_file("REUSE.toml", "M0S-E12-03")


@story("M0S-E12-03")
def test_contributing_covers_dco_tdd_and_styles() -> None:
    text = require_text("CONTRIBUTING.md", "M0S-E12-03").lower()
    for needle in ("git commit -s", "story", "red", "green", "no raw styles", "ai"):
        assert needle in text, f"CONTRIBUTING.md should cover {needle!r}"


@story("M0S-E12-03")
def test_security_and_code_of_conduct() -> None:
    sec = require_text("SECURITY.md", "M0S-E12-03").lower()
    assert "report" in sec and "main" in sec
    assert "contributor covenant" in require_text("CODE_OF_CONDUCT.md", "M0S-E12-03").lower()


@story("M0S-E12-03")
@pytest.mark.parametrize("form", ["bug.yml", "feature.yml", "story.yml", "theme.yml"])
def test_issue_forms(form: str) -> None:
    require_file(f".github/ISSUE_TEMPLATE/{form}", "M0S-E12-03")


@story("M0S-E12-03")
def test_pull_request_template() -> None:
    text = require_text(".github/pull_request_template.md", "M0S-E12-03")
    assert "M0S-" in text and re.search(r"signed-off-by|sign-off|dco", text, re.I)


@story("M0S-E12-03")
def test_null_home_assistant_bridge() -> None:
    text = require_text("services/core_api/src/hearthos_core/integrations/ha.py", "M0S-E12-03")
    assert "HomeAssistantBridge" in text and "class NullBridge" in text
