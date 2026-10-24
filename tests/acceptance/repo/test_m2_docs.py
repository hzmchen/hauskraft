# SPDX-License-Identifier: MIT
"""M2S-E10 static checks: the assistant docs for owners and plugin authors, README and CHANGELOG."""

from __future__ import annotations

import re

import pytest

from _support.red import require_text

story = pytest.mark.story


# ---------------------------------------------------------------- M2S-E10-01
@story("M2S-E10-01")
def test_owner_docs_cover_setup_privacy_and_limits() -> None:
    text = require_text("docs/assistant.md", "M2S-E10-01")
    for pattern in (r"(?i)zero data retention|ZDR", r"(?i)local", r"(?i)test connection", r"(?i)encrypt",
                    r"(?i)backup", r"(?i)re-?enter", r"(?i)private", r"(?i)undo", r"(?i)confirm",
                    r"(?i)switch.*off|turn.*off", r"(?i)usage", r"(?i)not (yet|there)|later"):
        assert re.search(pattern, text), f"docs/assistant.md should cover {pattern}"
    assert "docs/assistant.md" in require_text("README.md", "M2S-E10-01")
    assert re.search(r"(?i)M2\\?\*", require_text("docs/how-to-test.md", "M2S-E10-01"))


# ---------------------------------------------------------------- M2S-E10-02
@story("M2S-E10-02")
def test_plugin_author_guide() -> None:
    text = require_text("docs/plugins/tools-and-skills.md", "M2S-E10-02")
    for pattern in (r"ToolSpec", r"(?i)annotation", r"(?i)destructive", r"(?i)budget|tokens", r"(?i)compact",
                    r"SKILL\.md", r"(?i)untrusted", r"(?i)eval", r"(?i)undo", r"agent_guidance", r"(?i)problem code"):
        assert re.search(pattern, text), f"docs/plugins/tools-and-skills.md should cover {pattern}"


# ---------------------------------------------------------------- M2S-E10-03
@story("M2S-E10-03")
def test_changelog_and_readme_describe_m2() -> None:
    assert re.search(r"(?m)^###? M2\\?\* Agentic harness", require_text("CHANGELOG.md", "M2S-E10-03"))
    assert re.search(r"(?i)assistant", require_text("README.md", "M2S-E10-03"))
