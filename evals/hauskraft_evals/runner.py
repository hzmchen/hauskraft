# SPDX-License-Identifier: MIT
"""Run datasets case by case against one household and write the report (M2S-E09-01, ADR 0022)."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import anyio.to_thread
from pydantic_ai.models import Model
from pydantic_evals import Case, Dataset
from pydantic_evals.reporting import EvaluationReport

from hauskraft_core.assistant.prompt import prompt_version
from hauskraft_core.assistant.registry import tools_hash
from hauskraft_evals.checks import Expectations, Outcome
from hauskraft_evals.datasets import EvalCase, EvalDataset
from hauskraft_evals.household import Household
from hauskraft_evals.report import write_report


class TokenCapReachedError(RuntimeError):
    pass


@dataclass
class EvalConfig:
    model: str  # the name the report gives the model
    repeat: int | None  # overrides each dataset's own repeat
    max_tokens: int
    out_dir: Path
    judge_model: Model | None = None
    prices: tuple[float, float] | None = None  # per million input and output tokens


@dataclass
class RunResult:
    report: dict[str, object]
    json_path: Path
    markdown_path: Path
    stopped: str | None

    @property
    def exit_code(self) -> int:
        """0 when every dataset met its threshold, 1 when one missed it, 2 when the token cap stopped the run."""
        if self.stopped:
            return 2
        datasets = self.report["datasets"]
        assert isinstance(datasets, dict)  # noqa: S101 - built by _summary
        return 0 if all(d["passed"] for d in datasets.values()) else 1


@dataclass
class _Tally:
    max_tokens: int
    tokens: list[int] = field(default_factory=lambda: [0, 0])
    outcomes: list[Outcome] = field(default_factory=list)
    attempts: Counter[str] = field(default_factory=Counter)
    stopped: str | None = None

    def check(self) -> None:
        spent = sum(self.tokens)
        if spent >= self.max_tokens:
            self.stopped = f"Stopped: the token cap of {self.max_tokens:,} was reached ({spent:,} tokens used)."
            raise TokenCapReachedError(self.stopped)

    def add(self, outcome: Outcome) -> None:
        self.tokens[0] += outcome.input_tokens
        self.tokens[1] += outcome.output_tokens
        self.outcomes.append(outcome)


def _skill_versions(household: Household) -> dict[str, str]:
    versions = {}
    for skill_id, skill in sorted(household.app.state.skills.items()):
        payload = json.dumps([skill.instructions, skill.output, list(skill.tools)], sort_keys=True)
        versions[skill_id] = hashlib.sha256(payload.encode()).hexdigest()[:12]
    return versions


def _dataset_summary(
    ds: EvalDataset, report: EvaluationReport[EvalCase, Outcome, None], tally: _Tally
) -> dict[str, object]:
    passes: Counter[str] = Counter()
    reasons: dict[str, list[str]] = {}
    for rc in report.cases:
        name = rc.source_case_name or rc.name
        failed = {k: r.reason or "failed" for k, r in rc.assertions.items() if not r.value}
        if failed:
            reasons.setdefault(name, []).append("; ".join(f"{k}: {v}" for k, v in failed.items()))
        else:
            passes[name] += 1
    for failure in report.failures:
        if "token cap" not in failure.error_message:
            name = failure.source_case_name or failure.name
            reasons.setdefault(name, []).append(f"error: {failure.error_message[:300]}")
    cases = [
        {"name": c.name, "runs": tally.attempts[f"{ds.name}/{c.name}"], "passes": passes[c.name]} for c in ds.cases
    ]
    runs = sum(int(str(c["runs"])) for c in cases)
    rate = round(sum(passes.values()) / runs, 4) if runs else 0.0
    return {
        "pass_rate": rate,
        "threshold": ds.threshold,
        "passed": runs > 0 and rate >= ds.threshold,
        "cases": cases,
        "failures": [{"case": name, "reasons": rs} for name, rs in reasons.items()],
    }


def run_datasets(datasets: Sequence[EvalDataset], household: Household, config: EvalConfig) -> RunResult:
    """Run every case ``repeat`` times, one at a time (they share the household), and write the report."""
    started = dt.datetime.now(dt.UTC)
    tally = _Tally(config.max_tokens)
    summaries: dict[str, dict[str, object]] = {}
    for ds in datasets:

        async def task(case: EvalCase, ds_name: str = ds.name) -> Outcome:
            tally.check()
            tally.attempts[f"{ds_name}/{case.name}"] += 1

            def once() -> Outcome:
                household.prepare(case)
                return household.run(case)

            outcome = await anyio.to_thread.run_sync(once)
            tally.add(outcome)
            return outcome

        dataset = Dataset[EvalCase, Outcome, None](
            name=ds.name,
            cases=[Case(name=c.name, inputs=c, evaluators=(Expectations(config.judge_model),)) for c in ds.cases],
        )
        report = dataset.evaluate_sync(task, max_concurrency=1, progress=False, repeat=config.repeat or ds.repeat)
        summaries[ds.name] = _dataset_summary(ds, report, tally)

    tools = household.app.state.tool_registry.select(role="owner")
    data: dict[str, object] = {
        "model": config.model,
        "prompt_version": prompt_version(),
        "tools_hash": tools_hash(tools),
        "skills": _skill_versions(household),
        "started_at": started.isoformat(),
        "finished_at": dt.datetime.now(dt.UTC).isoformat(),
        "datasets": summaries,
        "tokens": {"input": tally.tokens[0], "output": tally.tokens[1]},
        "cost": _cost(tally.tokens, config.prices),
        "latency_ms": _latency([o.latency_ms for o in tally.outcomes]),
        "stopped": tally.stopped,
    }
    json_path, markdown_path = write_report(data, config.out_dir, started)
    return RunResult(data, json_path, markdown_path, tally.stopped)


def _cost(tokens: list[int], prices: tuple[float, float] | None) -> dict[str, float] | None:
    if prices is None:
        return None
    total = tokens[0] / 1e6 * prices[0] + tokens[1] / 1e6 * prices[1]
    return {"input_per_million": prices[0], "output_per_million": prices[1], "total": round(total, 4)}


def _latency(values: list[float]) -> dict[str, float]:
    if not values:
        return {"p50": 0.0, "p95": 0.0}
    ordered = sorted(values)

    def pick(q: float) -> float:
        return round(ordered[min(len(ordered) - 1, int(q * len(ordered)))], 1)

    return {"p50": pick(0.5), "p95": pick(0.95)}
