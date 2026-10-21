# SPDX-License-Identifier: MIT
"""E07 tasks plugin API (contract in docs/backlog/m0-star/E07-tasks-plugin.md)."""

from __future__ import annotations

import datetime as dt
import time
import uuid

import pytest

from _support.live import Api, assert_problem, unique

pytestmark = pytest.mark.live
story = pytest.mark.story

TASK_FIELDS = {"id", "title", "done", "done_at", "due_on", "data_class", "version", "created_by", "updated_by",
               "created_at", "updated_at"}


def _all(api: Api, **params) -> list[dict]:
    items, offset = [], 0
    while True:
        r = api.get("/tasks", params={**params, "limit": 200, "offset": offset})
        assert r.status_code == 200, r.text
        page = r.json()
        items += page["items"]
        offset += len(page["items"])
        if offset >= page["total"] or not page["items"]:
            return items


# ---------------------------------------------------------------- M0S-E07-03 CRUD
@story("M0S-E07-03")
def test_create_returns_task_and_location(demo: Api) -> None:
    title = unique("create")
    r = demo.post("/tasks", json={"title": f"  {title}  "})
    try:
        assert r.status_code == 201, r.text
        task = r.json()
        assert TASK_FIELDS <= set(task), set(task) ^ TASK_FIELDS
        assert task["title"] == title, "titles are trimmed"
        assert task["done"] is False and task["done_at"] is None and task["due_on"] is None
        assert task["data_class"] == "household" and task["version"] == 1
        assert task["created_by"]["display_name"] == "Demo Adult"
        assert r.headers.get("location", "").endswith(f"/tasks/{task['id']}")
    finally:
        if r.status_code == 201:
            demo.delete(f"/tasks/{r.json()['id']}")


@story("M0S-E07-03")
@pytest.mark.parametrize("body", [{"title": ""}, {"title": "   "}, {"title": "x" * 201}, {},
                                  {"title": "ok", "colour": "red"}, {"title": "ok", "due_on": "13.10.2026"}],
                         ids=["empty", "blank", "too-long", "missing", "unknown-field", "bad-date"])
def test_create_validation(demo: Api, body: dict) -> None:
    assert_problem(demo.post("/tasks", json=body), 422)


@story("M0S-E07-03")
def test_get_and_404(demo: Api, make_task) -> None:
    task = make_task(unique("get"))
    assert demo.get(f"/tasks/{task['id']}").json()["id"] == task["id"]
    assert_problem(demo.get(f"/tasks/{uuid.uuid4()}"), 404)


@story("M0S-E07-03")
def test_patch_title_and_due_date(demo: Api, make_task) -> None:
    task = make_task(unique("patch"))
    tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    r = demo.patch(f"/tasks/{task['id']}", json={"title": task["title"] + " v2", "due_on": tomorrow})
    assert r.status_code == 200, r.text
    assert r.json()["title"].endswith(" v2") and r.json()["due_on"] == tomorrow and r.json()["version"] == 2
    r = demo.patch(f"/tasks/{task['id']}", json={"due_on": None})
    assert r.json()["due_on"] is None


@story("M0S-E07-03")
def test_complete_and_reopen(demo: Api, make_task) -> None:
    task = make_task(unique("done"))
    done = demo.patch(f"/tasks/{task['id']}", json={"done": True}).json()
    assert done["done"] is True and done["done_at"]
    reopened = demo.patch(f"/tasks/{task['id']}", json={"done": False}).json()
    assert reopened["done"] is False and reopened["done_at"] is None


@story("M0S-E07-03")
def test_version_conflict(demo: Api, make_task) -> None:
    task = make_task(unique("conflict"))
    assert demo.patch(f"/tasks/{task['id']}", json={"title": task["title"] + "!", "version": 1}).status_code == 200
    assert_problem(demo.patch(f"/tasks/{task['id']}", json={"title": "stale", "version": 1}), 409, "version_conflict")


@story("M0S-E07-03")
def test_delete(demo: Api) -> None:
    task = demo.post("/tasks", json={"title": unique("delete")}).json()
    assert demo.delete(f"/tasks/{task['id']}").status_code == 204
    assert demo.get(f"/tasks/{task['id']}").status_code == 404


@story("M0S-E07-03")
def test_filter_and_sort_with_nulls_last(demo: Api, make_task) -> None:
    tag = unique("sort")
    today = dt.date.today()
    late = make_task(f"{tag} late", (today + dt.timedelta(days=5)).isoformat())
    none = make_task(f"{tag} none")
    soon = make_task(f"{tag} soon", (today + dt.timedelta(days=1)).isoformat())
    finished = make_task(f"{tag} finished")
    demo.patch(f"/tasks/{finished['id']}", json={"done": True})

    open_by_due = [t["id"] for t in _all(demo, status="open", sort="due_on") if t["title"].startswith(tag)]
    assert open_by_due == [soon["id"], late["id"], none["id"]]
    done_ids = {t["id"] for t in _all(demo, status="done") if t["title"].startswith(tag)}
    assert done_ids == {finished["id"]}
    newest_first = [t["id"] for t in _all(demo) if t["title"].startswith(tag)]
    assert newest_first == [finished["id"], soon["id"], none["id"], late["id"]]


@story("M0S-E07-03")
@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 201}, {"offset": -1}, {"status": "maybe"},
                                    {"sort": "title"}])
def test_list_parameter_validation(demo: Api, params: dict) -> None:
    assert_problem(demo.get("/tasks", params=params), 422)


@story("M0S-E07-03")
def test_pagination_envelope(demo: Api) -> None:
    body = demo.get("/tasks", params={"limit": 1, "offset": 0}).json()
    assert set(body) >= {"items", "total", "limit", "offset"} and body["limit"] == 1 and len(body["items"]) <= 1


# ---------------------------------------------------------------- M0S-E07-02 shared list + events
@story("M0S-E07-02")
def test_any_adult_can_edit_and_delete_any_task(demo: Api, alex: Api) -> None:
    task = demo.post("/tasks", json={"title": unique("shared")}).json()
    r = alex.patch(f"/tasks/{task['id']}", json={"title": task["title"] + " (by alex)"})
    assert r.status_code == 200 and r.json()["updated_by"]["display_name"] == "Alex Adult"
    assert r.json()["created_by"]["display_name"] == "Demo Adult"
    assert alex.delete(f"/tasks/{task['id']}").status_code == 204


@story("M0S-E07-02", "M0S-E10-03")
def test_each_write_appears_once_in_activity(demo: Api) -> None:
    task = demo.post("/tasks", json={"title": unique("events")}).json()
    demo.patch(f"/tasks/{task['id']}", json={"title": task["title"] + "!"})
    demo.patch(f"/tasks/{task['id']}", json={"done": True})
    demo.patch(f"/tasks/{task['id']}", json={"done": False})
    demo.delete(f"/tasks/{task['id']}")
    expected = ["hauskraft.task.created", "hauskraft.task.updated", "hauskraft.task.completed",
                "hauskraft.task.updated", "hauskraft.task.deleted"]
    deadline = time.time() + 15
    seen: list[str] = []
    while time.time() < deadline:
        items = demo.get("/activity", params={"limit": 50}).json()
        seen = [i["type"] for i in reversed(items) if i["subject"] == f"task/{task['id']}"]
        if len(seen) >= len(expected):
            break
        time.sleep(1)
    assert seen == expected, seen


# ---------------------------------------------------------------- M0S-E07-04 seed data
@story("M0S-E07-04")
def test_seeded_tasks_exist(demo: Api) -> None:
    titles = {t["title"]: t for t in _all(demo)}
    for name in ("Water the plants", "Take out recycling", "Book chimney sweep"):
        assert name in titles, f"seed task {name!r} missing"
    assert titles["Book chimney sweep"]["done"] is True
    assert titles["Take out recycling"]["due_on"] is not None
