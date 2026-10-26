# SPDX-License-Identifier: MIT
"""Eval reports: JSON for machines, markdown for people, and a comparison against a baseline."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


def _pct(value: float) -> str:
    return f"{value:.0%}"


def markdown(data: dict[str, Any]) -> str:
    lines = [
        f"# Eval report: {data['model']}",
        "",
        f"- Started: {data['started_at']}",
        f"- prompt_version: `{data['prompt_version']}` · tools_hash: `{data['tools_hash']}`",
        "- Skills: " + (", ".join(f"`{k}` {v}" for k, v in data["skills"].items()) or "none"),
        f"- Tokens: {data['tokens']['input']:,} input, {data['tokens']['output']:,} output"
        + (f" · estimated cost {data['cost']['total']}" if data.get("cost") else ""),
        f"- Latency per run: p50 {data['latency_ms']['p50']} ms, p95 {data['latency_ms']['p95']} ms",
    ]
    if data.get("stopped"):
        lines += ["", f"**{data['stopped']}**"]
    lines += ["", "| Dataset | Pass rate | Threshold | Result |", "|---|---|---|---|"]
    for name, ds in data["datasets"].items():
        result = "pass" if ds["passed"] else "**fail**"
        lines.append(f"| {name} | {_pct(ds['pass_rate'])} | {_pct(ds['threshold'])} | {result} |")
    for name, ds in data["datasets"].items():
        lines += ["", f"## {name}", "", "| Case | Passes |", "|---|---|"]
        lines += [f"| {c['name']} | {c['passes']}/{c['runs']} |" for c in ds["cases"]]
        for failure in ds["failures"]:
            lines.append(f"\n- **{failure['case']}**: " + " / ".join(failure["reasons"]))
    return "\n".join(lines) + "\n"


def write_report(data: dict[str, Any], out_dir: Path, started: dt.datetime) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{started:%Y%m%dT%H%M%SZ}-{re.sub(r'[^A-Za-z0-9.-]+', '-', str(data['model'])).strip('-')}"
    json_path, md_path = out_dir / f"{stem}.json", out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(markdown(data), encoding="utf-8")
    return json_path, md_path


def compare(report_path: Path, baseline_path: Path) -> str:
    """Pass rates per dataset and tokens of a report next to a baseline's, with the differences."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    base = json.loads(baseline_path.read_text(encoding="utf-8"))
    lines = [
        f"{report['model']} ({report['prompt_version']}) vs {base['model']} ({base['prompt_version']})",
        "",
        "| Dataset | Report | Baseline | Change |",
        "|---|---|---|---|",
    ]
    for name in sorted(set(report["datasets"]) | set(base["datasets"])):
        now = report["datasets"].get(name, {}).get("pass_rate")
        then = base["datasets"].get(name, {}).get("pass_rate")
        change = f"{now - then:+.0%}" if now is not None and then is not None else "n/a"
        lines.append(
            f"| {name} | {_pct(now) if now is not None else '-'} | {_pct(then) if then is not None else '-'} "
            f"| {change} |"
        )
    lines.append("")
    for kind in ("input", "output"):
        now, then = report["tokens"][kind], base["tokens"][kind]
        lines.append(f"{kind.title()} tokens: {now:,} vs {then:,} ({now - then:+,})")
    return "\n".join(lines)
