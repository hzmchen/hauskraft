# SPDX-License-Identifier: MIT
"""M2S-E09-01: the runner drives the real harness in-process; Pydantic AI's FunctionModel stands in for a model."""

import json
import re
from pathlib import Path

import pytest
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from hauskraft_core.settings import Settings
from hauskraft_evals.datasets import EvalDataset
from hauskraft_evals.household import Household
from hauskraft_evals.report import compare
from hauskraft_evals.runner import EvalConfig, run_datasets

pytestmark = pytest.mark.integration
FIXTURE = {"tasks": [{"title": "Plan the garden"}], "today": "2026-11-02", "timezone": "Europe/Berlin"}


def scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """Add 'X' creates X; Delete 'X' lists, then deletes X; anything else gets a short answer."""
    request = messages[-1]
    assert isinstance(request, ModelRequest)
    prompt = next(
        p.content for m in messages if isinstance(m, ModelRequest) for p in m.parts if isinstance(p, UserPromptPart)
    )
    title = re.search(r"'(.+?)'", str(prompt))
    returned = [p for p in request.parts if isinstance(p, ToolReturnPart)]
    german = "Language: German" in (info.instructions or "")
    if str(prompt).startswith("Add") and title:
        if not returned:
            return ModelResponse(parts=[ToolCallPart("tasks_create", {"title": title[1]})])
        return ModelResponse(parts=[TextPart("Ich habe die Aufgabe hinzugefügt." if german else "I added the task.")])
    if str(prompt).startswith("Delete") and title:
        if not returned:
            return ModelResponse(parts=[ToolCallPart("tasks_list", {"status": "all"})])
        if returned[0].tool_name == "tasks_list":
            items = returned[0].content["items"] if isinstance(returned[0].content, dict) else []
            found = next(t["id"] for t in items if t["title"] == title[1])
            return ModelResponse(parts=[ToolCallPart("tasks_delete", {"task_id": found})])
        return ModelResponse(parts=[TextPart("Okay, I left the task as it is.")])
    return ModelResponse(parts=[TextPart("I can help with your tasks.")])


def dataset(name: str, cases: list[dict[str, object]], threshold: float = 1.0) -> EvalDataset:
    return EvalDataset.model_validate({"name": name, "threshold": threshold, "repeat": 1, "cases": cases})


ADD = {
    "name": "add milk",
    "fixture": {**FIXTURE, "language": "en"},
    "input": {"message": "Add 'Buy milk'"},
    "expect": {
        "tool_calls": [{"name": "tasks.create", "args": {"title": "buy milk"}}],
        "no_tool_calls": ["tasks.delete"],
        "state": {"exists": ["Buy milk", "Plan the garden"]},
        "answer_language": "en",
    },
}
DENIED = {
    "name": "a denied delete changes nothing",
    "fixture": {**FIXTURE, "language": "en", "role": "adult"},
    "input": {"message": "Delete 'Plan the garden'", "confirm": "denied"},
    "expect": {"paused_for_confirmation": True, "state": {"exists": ["Plan the garden"]}},
}
GERMAN = {
    "name": "answers in German",
    "fixture": {**FIXTURE, "language": "de"},
    "input": {"message": "Add 'Milch kaufen'"},
    "expect": {"answer_language": "de", "answer_contains": ["hinzugef"]},
}


@pytest.fixture
def household(db_settings: Settings) -> Household:
    with Household(db_settings, model=FunctionModel(scripted)) as h:
        yield h


def test_cases_run_against_the_real_harness_and_write_a_report(household: Household, tmp_path: Path) -> None:
    config = EvalConfig(model="function-model", repeat=None, max_tokens=200_000, out_dir=tmp_path)
    result = run_datasets([dataset("demo", [ADD, DENIED, GERMAN])], household, config)
    report = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert report["datasets"]["demo"]["cases"] == [
        {"name": "add milk", "runs": 1, "passes": 1},
        {"name": "a denied delete changes nothing", "runs": 1, "passes": 1},
        {"name": "answers in German", "runs": 1, "passes": 1},
    ], result.markdown_path.read_text(encoding="utf-8")
    assert report["datasets"]["demo"]["pass_rate"] == 1.0
    assert result.exit_code == 0
    assert {"model", "prompt_version", "tools_hash", "skills", "started_at", "tokens", "latency_ms"} <= set(report)
    assert report["model"] == "function-model"
    assert report["tokens"]["input"] > 0
    assert "| demo | 100% |" in result.markdown_path.read_text(encoding="utf-8")


def test_a_missed_threshold_fails_the_run(household: Household, tmp_path: Path) -> None:
    wrong = {**ADD, "name": "expects the wrong state", "expect": {"state": {"missing": ["Buy milk"]}}}
    config = EvalConfig(model="function-model", repeat=2, max_tokens=200_000, out_dir=tmp_path)
    result = run_datasets([dataset("demo", [ADD, wrong], threshold=0.9)], household, config)
    report = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert report["datasets"]["demo"]["cases"][1] == {"name": "expects the wrong state", "runs": 2, "passes": 0}
    assert report["datasets"]["demo"]["pass_rate"] == 0.5
    assert report["datasets"]["demo"]["passed"] is False
    assert result.exit_code == 1
    # The answer is in the reasons, so a failed run can be understood from the report alone.
    assert "answer: 'I added the task.'" in report["datasets"]["demo"]["failures"][0]["reasons"][0]


def test_the_token_cap_stops_the_run(household: Household, tmp_path: Path) -> None:
    config = EvalConfig(model="function-model", repeat=3, max_tokens=1, out_dir=tmp_path)
    result = run_datasets([dataset("demo", [ADD])], household, config)
    assert result.stopped is not None
    assert "token cap" in result.stopped
    assert result.exit_code == 2
    assert json.loads(result.json_path.read_text(encoding="utf-8"))["datasets"]["demo"]["cases"][0]["runs"] == 1


def test_compare_prints_pass_rate_and_token_differences(household: Household, tmp_path: Path) -> None:
    config = EvalConfig(model="function-model", repeat=None, max_tokens=200_000, out_dir=tmp_path)
    first = run_datasets([dataset("demo", [ADD])], household, config).json_path
    data = json.loads(first.read_text(encoding="utf-8"))
    data["datasets"]["demo"]["pass_rate"] = 0.5
    data["tokens"]["input"] -= 10
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps(data), encoding="utf-8")
    text = compare(first, baseline)
    assert "demo" in text
    assert "+50%" in text
    assert "+10" in text
