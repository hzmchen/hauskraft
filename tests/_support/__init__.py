# SPDX-License-Identifier: MIT
"""Helpers shared by the HearthOS acceptance suite. See tests/README.md."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TESTS = REPO / "tests"
FIXTURES = TESTS / "fixtures"
BACKLOG = REPO / "docs" / "backlog" / "m0-star"
SPEC = REPO / "docs" / "spec" / "hearthos-spec-v0.2.md"
STATUS_FILE = TESTS / "story-status.json"
