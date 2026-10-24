# SPDX-License-Identifier: MIT
"""Helpers shared by the Hauskraft acceptance suite. See tests/README.md."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TESTS = REPO / "tests"
FIXTURES = TESTS / "fixtures"
BACKLOG_ROOT = REPO / "docs" / "backlog"  # one m<N>-star folder per milestone
SPEC = REPO / "docs" / "spec" / "hauskraft-spec-v0.4.md"
STATUS_FILE = TESTS / "story-status.json"
