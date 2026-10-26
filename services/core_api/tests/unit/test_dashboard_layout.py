# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E08-06 default layouts; M2S-E06-06: a widget can stay out of them (``"default_layout": false``)."""

import pytest

from hauskraft_core.dashboard.service import default_layout

pytestmark = pytest.mark.unit

TASKS = "dev.hauskraft.tasks"


def test_widgets_are_placed_left_to_right_at_their_default_size() -> None:
    cells = default_layout([(TASKS, {"id": "a", "default_size": {"w": 8, "h": 6}}), (TASKS, {"id": "b"})])
    assert [(c.widget_id, c.x, c.y, c.w, c.h) for c in cells] == [("a", 0, 0, 8, 6), ("b", 8, 0, 4, 4)]


def test_a_widget_that_opts_out_is_left_out_and_takes_no_space() -> None:
    widgets = [
        (TASKS, {"id": "tasks.list", "default_size": {"w": 4, "h": 6}}),
        (TASKS, {"id": "tasks.overview", "default_layout": False}),
        (TASKS, {"id": "later", "default_layout": True}),
    ]
    assert [(c.widget_id, c.x) for c in default_layout(widgets)] == [("tasks.list", 0), ("later", 4)]
