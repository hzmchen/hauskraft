# SPDX-License-Identifier: MIT
"""Backlog and traceability tooling for HearthOS.

    python scripts/backlog_tools.py check                # integrity of spec, backlog and story status
    python scripts/backlog_tools.py coverage             # print story -> acceptance tests
    python scripts/backlog_tools.py coverage --write     # regenerate docs/testing/traceability.md

Standard library only, so it runs before the workspace exists. Used by tests/meta.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BACKLOG = REPO / "docs" / "backlog" / "m0-star"
SPEC = REPO / "docs" / "spec" / "hearthos-spec-v0.2.md"
STATUS = REPO / "tests" / "story-status.json"
TRACE = REPO / "docs" / "testing" / "traceability.md"

STORY_HEADING = re.compile(r"^## (M0S-E\d{2}-\d{2}) · (.+)$", re.M)
STORY_REF = re.compile(r"E\d{2}-\d{2}")
REQUIRED_FIELDS = ("Story", "AC", "Tech", "Tests", "Deps")


@dataclass
class Story:
    id: str
    title: str
    file: str
    body: str
    deps: list[str] = field(default_factory=list)
    estimate: str = ""
    labels: str = ""


def parse_stories() -> dict[str, Story]:
    stories: dict[str, Story] = {}
    for path in sorted(BACKLOG.glob("E[0-9][0-9]-*.md")):
        text = path.read_text(encoding="utf-8")
        heads = list(STORY_HEADING.finditer(text))
        for i, m in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            body = text[m.end():end]
            sid = m.group(1)
            if sid in stories:
                raise ValueError(f"duplicate story id {sid}")
            dep_line = re.search(r"\*\*Deps:\*\*\s*(.*?)\s*·\s*\*\*Est:\*\*\s*(\w+)\s*·\s*\*\*Labels:\*\*\s*(.*)", body)
            deps = [f"M0S-{d}" for d in STORY_REF.findall(dep_line.group(1))] if dep_line else []
            stories[sid] = Story(sid, m.group(2).strip(), path.name, body, deps,
                                 dep_line.group(2) if dep_line else "", dep_line.group(3).strip() if dep_line else "")
    return stories


def readme_totals() -> tuple[dict[str, int], int]:
    text = (BACKLOG / "README.md").read_text(encoding="utf-8")
    per_epic = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\| (E\d{2}) \| [^|]+ \| (\d+) \|", text, re.M)}
    total = re.search(r"\| \*\*Total\*\* \| \*\*(\d+)\*\* \|", text)
    return per_epic, int(total.group(1)) if total else -1


def spec_sections() -> set[str]:
    text = SPEC.read_text(encoding="utf-8")
    return {m.group(1).rstrip(".") for m in re.finditer(r"^#{2,4} (\d+(?:\.\d+)*)\.?\s", text, re.M)}


def find_cycles(stories: dict[str, Story]) -> list[list[str]]:
    cycles, state = [], {}

    def visit(n: str, path: list[str]) -> None:
        if state.get(n) == 1:
            cycles.append(path[path.index(n):] + [n])
            return
        if state.get(n) == 2:
            return
        state[n] = 1
        for d in stories[n].deps:
            if d in stories:
                visit(d, path + [n])
        state[n] = 2

    for sid in stories:
        visit(sid, [])
    return cycles


def load_status() -> dict[str, dict[str, str]]:
    return json.loads(STATUS.read_text(encoding="utf-8"))["stories"]


PY_STORY = re.compile(r"""story\(([^)]*)\)""")
ID_IN = re.compile(r"""["'](M0S-E\d{2}-\d{2})["']""")


def coverage() -> dict[str, list[str]]:
    """Map story id -> test files (pytest modules and Playwright specs) that reference it."""
    cov: dict[str, set[str]] = {}
    files = [*sorted((REPO / "tests").rglob("test_*.py")), *sorted((REPO / "tests" / "e2e").glob("*.spec.ts"))]
    for path in files:
        if "_support" in path.parts or "fixtures" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        ids: set[str] = set()
        # A test module covers every story id it names as a string literal (markers, params, RED hints).
        if PY_STORY.search(text):
            ids.update(ID_IN.findall(text))
        consts = dict(re.findall(r'const (\w+) = "(M0S-E\d{2}-\d{2})"', text))
        for name, sid in consts.items():
            if re.search(rf"story\([^)]*\b{name}\b", text):
                ids.add(sid)
        rel = str(path.relative_to(REPO))
        for sid in ids:
            cov.setdefault(sid, set()).add(rel)
    return {k: sorted(v) for k, v in sorted(cov.items())}


def check() -> list[str]:
    problems: list[str] = []
    stories = parse_stories()
    for s in stories.values():
        for f in REQUIRED_FIELDS:
            if f"**{f}:**" not in s.body:
                problems.append(f"{s.id}: missing **{f}:** field")
        if s.estimate not in ("S", "M"):
            problems.append(f"{s.id}: estimate must be S or M, got {s.estimate!r}")
        for d in s.deps:
            if d not in stories:
                problems.append(f"{s.id}: depends on unknown story {d}")
    for cyc in find_cycles(stories):
        problems.append("dependency cycle: " + " -> ".join(cyc))

    per_epic, total = readme_totals()
    if total != len(stories):
        problems.append(f"README total {total} != {len(stories)} stories in epic files")
    counted: dict[str, int] = {}
    for sid in stories:
        counted[sid[4:7]] = counted.get(sid[4:7], 0) + 1
    for epic, n in per_epic.items():
        if counted.get(epic, 0) != n:
            problems.append(f"README says {epic} has {n} stories, epic file has {counted.get(epic, 0)}")

    sections = spec_sections()
    for path in sorted(BACKLOG.glob("*.md")):
        for ref in re.findall(r"§(\d+(?:\.\d+)*)", path.read_text(encoding="utf-8")):
            if ref.rstrip(".") not in sections:
                problems.append(f"{path.name}: §{ref} not found in the spec")

    status = load_status()
    if set(status) != set(stories):
        problems.append(f"story-status.json mismatch: missing {sorted(set(stories) - set(status))}, "
                        f"extra {sorted(set(status) - set(stories))}")
    cov = coverage()
    for sid, entry in status.items():
        if entry.get("status") not in ("red", "green"):
            problems.append(f"{sid}: status must be red or green")
        if entry.get("acceptance") not in ("suite", "in-story"):
            problems.append(f"{sid}: acceptance must be suite or in-story")
        if entry.get("acceptance") == "suite" and sid not in cov:
            problems.append(f"{sid}: marked 'suite' but no acceptance test references it")
    for sid in cov:
        if sid not in stories:
            problems.append(f"tests reference unknown story {sid}")
    return problems


def write_traceability() -> str:
    stories, status, cov = parse_stories(), load_status(), coverage()
    lines = [
        "# Traceability: stories to acceptance tests",
        "",
        "Generated by `python scripts/backlog_tools.py coverage --write`. Do not edit by hand.",
        "",
        "`suite` stories have spec-owned acceptance tests that must go from red to green. "
        "`in-story` stories are covered by tests the implementer writes first (red) inside the story. "
        "Status lives in `tests/story-status.json`.",
        "",
        "| Story | Title | Status | Acceptance | Tests |",
        "|---|---|---|---|---|",
    ]
    for sid, s in stories.items():
        st = status.get(sid, {})
        tests = "<br>".join(f"`{t}`" for t in cov.get(sid, [])) or "written in-story"
        lines.append(f"| {sid} | {s.title} | {st.get('status', '?')} | {st.get('acceptance', '?')} | {tests} |")
    suite = sum(1 for v in status.values() if v.get("acceptance") == "suite")
    lines += ["", f"{len(stories)} stories: {suite} with suite acceptance tests, {len(stories) - suite} in-story.", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    cov = sub.add_parser("coverage")
    cov.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if args.cmd == "check":
        problems = check()
        for p in problems:
            print(p)
        print("OK" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0
    text = write_traceability()
    if args.write:
        TRACE.parent.mkdir(parents=True, exist_ok=True)
        TRACE.write_text(text, encoding="utf-8")
        print(f"wrote {TRACE.relative_to(REPO)}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
