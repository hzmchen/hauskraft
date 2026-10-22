# SPDX-License-Identifier: MIT
"""E06-03/04 plugin loading and registry API, E08-06 dashboard layouts, E10-03 activity feed."""

from __future__ import annotations

import time

import pytest

from _support.live import Api, assert_problem, unique

pytestmark = pytest.mark.live
story = pytest.mark.story


def _plugins(api: Api) -> dict[str, dict]:
    r = api.get("/plugins")
    assert r.status_code == 200, r.text
    return {p["id"]: p for p in r.json()}


# ---------------------------------------------------------------- M0S-E06-03 loader
@story("M0S-E06-03")
def test_tasks_plugin_is_loaded_in_process(demo: Api) -> None:
    tasks = _plugins(demo).get("dev.hauskraft.tasks")
    assert tasks, "tasks plugin not listed"
    assert tasks["kind"] == "inprocess" and tasks["enabled"] is True and tasks["load_error"] is None
    assert demo.get("/tasks").status_code == 200, "plugin router must be mounted under /api/v1/tasks"


@story("M0S-E06-03", "M0S-E13-06")
@pytest.mark.parametrize("theme", ["default", "paper", "hackspace"])
def test_builtin_themes_are_declarative_plugins(demo: Api, theme: str) -> None:
    p = _plugins(demo).get(f"dev.hauskraft.theme.{theme}")
    assert p and p["kind"] == "declarative" and p["type"] == ["theme"] and p["load_error"] is None, p


# ---------------------------------------------------------------- M0S-E06-04 registry API
@story("M0S-E06-04")
def test_contributions_are_exposed(demo: Api) -> None:
    tasks = _plugins(demo)["dev.hauskraft.tasks"]
    assert {"id", "name", "version", "kind", "type", "enabled", "contributes", "load_error"} <= set(tasks)
    assert [w["id"] for w in tasks["contributes"]["widgets"]] == ["tasks.list"]
    assert [p["id"] for p in tasks["contributes"]["pages"]] == ["tasks"]


@story("M0S-E06-04")
def test_toggle_reports_restart_required(demo: Api) -> None:
    r = demo.patch("/plugins/dev.hauskraft.tasks", json={"enabled": True})
    assert r.status_code == 200, r.text
    assert r.json().get("restart_required") is True


@story("M0S-E06-04")
def test_theme_plugins_cannot_be_toggled(demo: Api) -> None:
    assert_problem(demo.patch("/plugins/dev.hauskraft.theme.paper", json={"enabled": False}), 422, "use_theme_settings")


# ---------------------------------------------------------------- M0S-E08-06 dashboard
@story("M0S-E08-06")
def test_default_layout_contains_tasks_widget(alex: Api) -> None:
    r = alex.get("/dashboard/today")
    assert r.status_code == 200, r.text
    layout = r.json()["layout"]
    assert any(c["plugin_id"] == "dev.hauskraft.tasks" and c["widget_id"] == "tasks.list" for c in layout), layout
    for cell in layout:
        assert {"i", "plugin_id", "widget_id", "x", "y", "w", "h"} <= set(cell)
        assert 0 <= cell["x"] and cell["x"] + cell["w"] <= 12, "grid has 12 columns"


@story("M0S-E08-06")
def test_layout_round_trip(demo: Api) -> None:
    original = demo.get("/dashboard/today").json()["layout"]
    moved = [dict(c, x=0, y=c["y"] + 1, w=6) for c in original]
    try:
        r = demo.put("/dashboard/today", json={"layout": moved})
        assert r.status_code == 200, r.text
        assert demo.get("/dashboard/today").json()["layout"] == moved
    finally:
        demo.put("/dashboard/today", json={"layout": original})


@story("M0S-E08-06")
def test_layout_rejects_cells_outside_grid(demo: Api) -> None:
    bad = [{"i": "x", "plugin_id": "dev.hauskraft.tasks", "widget_id": "tasks.list", "x": 10, "y": 0, "w": 6, "h": 4}]
    assert_problem(demo.put("/dashboard/today", json={"layout": bad}), 422)


# ---------------------------------------------------------------- M0S-E10-03 activity
@story("M0S-E10-03")
def test_activity_shows_actor_and_is_newest_first(demo: Api) -> None:
    task = demo.post("/tasks", json={"title": unique("activity")}).json()
    try:
        deadline, entry = time.time() + 15, None
        while time.time() < deadline and entry is None:
            items = demo.get("/activity", params={"limit": 50}).json()
            entry = next((i for i in items if i["subject"] == f"task/{task['id']}"), None)
            time.sleep(0.5)
        assert entry, "created event never reached the activity feed"
        assert entry["type"] == "hauskraft.task.created"
        assert entry["actor"]["display_name"] == "Demo Adult"
        assert {"id", "type", "time", "actor", "subject", "summary_key", "data"} <= set(entry)
        times = [i["time"] for i in items]
        assert times == sorted(times, reverse=True), "activity must be newest first"
    finally:
        demo.delete(f"/tasks/{task['id']}")


@story("M0S-E10-03")
def test_activity_pagination(demo: Api) -> None:
    first = demo.get("/activity", params={"limit": 2}).json()
    assert len(first) <= 2
    if len(first) == 2:
        older = demo.get("/activity", params={"limit": 2, "before": first[-1]["time"]}).json()
        assert all(i["time"] < first[-1]["time"] for i in older)
