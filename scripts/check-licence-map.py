#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Enforce the HearthOS licence map (spec §4.2, ADR-0003, M0S-E02-04).

    python scripts/check-licence-map.py [--root DIR]

Every file under a mapped path must carry exactly the licence the map requires, either in an
SPDX header or through a REUSE.toml annotation:

    themes/**/assets/fonts/**                                   OFL-1.1
    services/**, apps/**                                        AGPL-3.0-or-later
    packages/**, plugins/official/**, themes/**, integrations/** MIT

Prints every offending file and exits 1 if there is any. Standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

# First match wins, so the most specific rule comes first.
LICENCE_MAP: list[tuple[str, str]] = [
    ("themes/**/assets/fonts/**", "OFL-1.1"),
    ("services/**", "AGPL-3.0-or-later"),
    ("apps/**", "AGPL-3.0-or-later"),
    ("packages/**", "MIT"),
    ("plugins/official/**", "MIT"),
    ("themes/**", "MIT"),
    ("integrations/**", "MIT"),
]

SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", "dist"}
# Licence texts themselves are not licensed files (REUSE spec).
LICENCE_FILE = re.compile(r"^(LICEN[CS]E|COPYING)(\..*)?$|^.*\.license$", re.I)
# REUSE-IgnoreStart
SPDX_TAG = re.compile(r"SPDX-License-Identifier:[ \t]*([A-Za-z0-9.+() \t-]+?)[ \t]*(?:-->|\*/|[\"'\n]|$)", re.M)
# REUSE-IgnoreEnd
SPDX_ID = re.compile(r"[A-Za-z0-9.+-]+")
HEADER_BYTES = 4096


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """REUSE.toml glob: `*` stays within a path segment, `**` crosses segments."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


@dataclass(frozen=True)
class Annotation:
    patterns: tuple[re.Pattern[str], ...]
    licences: frozenset[str]
    precedence: str

    def matches(self, rel: str) -> bool:
        return any(p.match(rel) for p in self.patterns)


def licence_ids(expression: str) -> set[str]:
    return {t for t in SPDX_ID.findall(expression) if t.upper() not in {"AND", "OR", "WITH"}}


def load_annotations(root: Path) -> list[Annotation]:
    toml_path = root / "REUSE.toml"
    if not toml_path.exists():
        return []
    data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    annotations = []
    for entry in data.get("annotations", []):
        paths = entry.get("path", [])
        paths = [paths] if isinstance(paths, str) else paths
        expr = entry.get("SPDX-License-Identifier", "")
        exprs = [expr] if isinstance(expr, str) else expr
        ids = frozenset(i for e in exprs for i in licence_ids(e))
        annotations.append(Annotation(tuple(glob_to_regex(p) for p in paths), ids, entry.get("precedence", "closest")))
    return annotations


def header_licences(path: Path) -> set[str]:
    try:
        head = path.read_bytes()[:HEADER_BYTES].decode("utf-8", errors="ignore")
    except OSError:
        return set()
    return {i for m in SPDX_TAG.finditer(head) for i in licence_ids(m.group(1))}


def effective_licences(rel: str, path: Path, annotations: list[Annotation]) -> set[str]:
    own = header_licences(path)
    matching = [a for a in annotations if a.matches(rel)]
    if not matching:
        return own
    last = matching[-1]  # REUSE: when several annotations match, the last one wins
    if last.precedence == "override" or not own:
        return set(last.licences)
    if last.precedence == "aggregate":
        return own | last.licences
    return own  # "closest": the file's own information wins


def required_licence(rel: str) -> str | None:
    for pattern, licence in LICENCE_MAP:
        if glob_to_regex(pattern).match(rel):
            return licence
    return None


def iter_files(root: Path):  # type: ignore[no-untyped-def]
    for path in sorted(root.rglob("*")):
        rel_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in rel_parts) or not path.is_file():
            continue
        if LICENCE_FILE.match(path.name) or "LICENSES" in rel_parts:
            continue
        yield path


def check(root: Path) -> list[str]:
    annotations = load_annotations(root)
    problems = []
    for path in iter_files(root):
        rel = path.relative_to(root).as_posix()
        required = required_licence(rel)
        if required is None:
            continue
        found = effective_licences(rel, path, annotations)
        if found != {required}:
            shown = " AND ".join(sorted(found)) if found else "no licence"
            problems.append(f"{rel}: expected {required}, found {shown}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root to check (default: this repository)",
    )
    args = parser.parse_args(argv)
    problems = check(args.root.resolve())
    for line in problems:
        print(line)
    if problems:
        print(
            f"\n{len(problems)} file(s) violate the licence map (spec §4.2). Fix the SPDX header or REUSE.toml.",
            file=sys.stderr,
        )
        return 1
    print("licence map OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
