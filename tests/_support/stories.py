# SPDX-License-Identifier: MIT
"""Story status registry: which backlog stories are red (not done) or green (done).

tests/story-status.json is the single switch that decides whether a story's acceptance
tests are expected to fail (red) or must pass (green). Flipping a story to green is part
of that story's Definition of Done. See docs/testing/README.md.
"""

from __future__ import annotations

import json
import re

from . import STATUS_FILE

STORY_ID = re.compile(r"^M0S-E\d{2}-\d{2}$")
STATUSES = {"red", "green"}
ACCEPTANCE_KINDS = {"suite", "in-story"}


def load() -> dict[str, dict[str, str]]:
    data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    return data["stories"]


def status_of(stories: dict[str, dict[str, str]], story_id: str) -> str:
    return stories[story_id]["status"]
