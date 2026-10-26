# SPDX-License-Identifier: MIT
"""Deterministic checks of one run against a case's ``expect``; an LLM judge only for rubric cases (ADR 0022)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai.models import Model
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext
from pydantic_evals.evaluators.llm_as_a_judge import judge_output

from hauskraft_evals.datasets import EvalCase, ExpectedCall, ExpectedState

# Common short words, enough to tell English from German in an assistant's answer. Quoted text (task titles) is
# left out first, so "Milch kaufen" in an English answer doesn't count.
_WORDS = {
    "en": set(
        "the and is are you your to of a an in it for on with have has this that there no not i've i "
        "added done open due today tomorrow task tasks week left nothing".split()
    ),
    "de": set(
        "der die das und ist sind du dein deine zu von ein eine im für auf mit hast hat diese dass es keine nicht "
        "ich habe hinzugefügt erledigt offen offene fällig heute morgen aufgabe aufgaben woche noch nichts".split()
    ),
}
# Straight, German (low-high double and single) and French quotes, and backticks.
_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"|\u201e[^\u201c]*\u201c|\u201a[^\u2018]*\u2018|\u00ab[^\u00bb]*\u00bb|`[^`]*`")


def language_of(text: str) -> str | None:
    """``en``, ``de``, or None when the answer has too few common words to tell."""
    words = re.findall(r"[a-zäöüß']+", _QUOTED.sub(" ", text.lower()))
    counts = {lang: sum(w in vocab for w in words) for lang, vocab in _WORDS.items()}
    best = max(counts, key=lambda lang: counts[lang])
    others = [n for lang, n in counts.items() if lang != best]
    return best if counts[best] >= 2 and counts[best] > max(others) else None


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]
    ok: bool | None  # None: never answered (the run paused or ended first)


@dataclass
class Outcome:
    """What one run of a case did, as the checks see it."""

    answer: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    paused: bool = False
    tasks: list[dict[str, Any]] = field(default_factory=list)
    status: str = "done"
    error_code: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0


def _same(expected: Any, actual: Any) -> bool:
    if isinstance(expected, str) and isinstance(actual, str):
        return expected.strip().casefold() == actual.strip().casefold()
    if isinstance(expected, dict) and isinstance(actual, dict):
        return all(k in actual and _same(v, actual[k]) for k, v in expected.items())
    return bool(expected == actual)


def _called(expected: ExpectedCall, calls: list[ToolCall]) -> bool:
    return any(c.name == expected.name and _same(expected.args, c.args) for c in calls)


def _state(expected: ExpectedState, tasks: list[dict[str, Any]]) -> EvaluationReason:
    by_title = {str(t["title"]).strip().casefold(): t for t in tasks}
    problems = [f"missing {t!r}" for t in expected.exists if t.casefold() not in by_title]
    problems += [f"still there: {t!r}" for t in expected.missing if t.casefold() in by_title]
    problems += [f"not done: {t!r}" for t in expected.done if not by_title.get(t.casefold(), {}).get("done")]
    problems += [f"not open: {t!r}" for t in expected.open if by_title.get(t.casefold(), {"done": True})["done"]]
    if expected.count is not None and len(tasks) != expected.count:
        problems.append(f"{len(tasks)} tasks, expected {expected.count}")
    return EvaluationReason(not problems, "; ".join(problems) or None)


@dataclass
class Expectations(Evaluator[EvalCase, Outcome, None]):
    """One assertion per ``expect`` key; the run passes when all of them hold."""

    judge_model: Model | None = None

    async def evaluate(self, ctx: EvaluatorContext[EvalCase, Outcome, None]) -> dict[str, EvaluationReason]:
        expect, out = ctx.inputs.expect, ctx.output
        results: dict[str, EvaluationReason] = {}
        if expect.tool_calls is not None:
            missing = [c.name for c in expect.tool_calls if not _called(c, out.tool_calls)]
            seen = ", ".join(f"{c.name}({c.args})" for c in out.tool_calls) or "none"
            results["tool_calls"] = EvaluationReason(
                not missing, f"not called: {missing}; calls: {seen}" if missing else None
            )
        if expect.no_tool_calls is not None:
            banned = set(expect.no_tool_calls)
            hit = [c.name for c in out.tool_calls if "*" in banned or c.name in banned]
            results["no_tool_calls"] = EvaluationReason(not hit, f"called {hit}" if hit else None)
        if expect.paused_for_confirmation is not None:
            results["paused_for_confirmation"] = EvaluationReason(
                out.paused == expect.paused_for_confirmation, f"paused: {out.paused}"
            )
        if expect.state is not None:
            results["state"] = _state(expect.state, out.tasks)
        if expect.answer_language is not None:
            got = language_of(out.answer)
            results["answer_language"] = EvaluationReason(got == expect.answer_language, f"answer language: {got}")
        if expect.answer_contains is not None:
            absent = [p for p in expect.answer_contains if not re.search(p, out.answer, re.IGNORECASE | re.DOTALL)]
            results["answer_contains"] = EvaluationReason(not absent, f"no match for {absent}" if absent else None)
        if expect.judge is not None:
            results["judge"] = await self._judge(expect.judge, out.answer)
        return results

    async def _judge(self, rubric: str, answer: str) -> EvaluationReason:
        if self.judge_model is None:
            return EvaluationReason(False, "no judge model configured")
        grading = await judge_output(answer, rubric, self.judge_model)
        return EvaluationReason(grading.pass_, grading.reason)
