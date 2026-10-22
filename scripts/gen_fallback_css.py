#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate @hauskraft/ui's fallback tokens from the built-in Default theme (M0S-E08-01).

    uv run python scripts/gen_fallback_css.py            write packages/ui/src/tokens/fallback.css
    uv run python scripts/gen_fallback_css.py --check    exit 1 if the file is stale

The shell loads this before /api/v1/theme/active.css, so the UI is styled even when the theme stylesheet
cannot be fetched (spec §10.2.8). It is the Default theme compiled by the real compiler, without
@font-face rules (fonts are served by the API).
"""

from __future__ import annotations

import sys
from pathlib import Path

from hauskraft_core.themes.validate import validate_theme

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "packages" / "ui" / "src" / "tokens" / "fallback.css"
# REUSE-IgnoreStart
HEADER = (
    "/* SPDX-License-Identifier: MIT */\n"
    "/* GENERATED from themes/builtin/default by scripts/gen_fallback_css.py. Do not edit; run `just gen`. */\n"
)
# REUSE-IgnoreEnd


def render() -> str:
    report = validate_theme(REPO / "themes" / "builtin" / "default")
    if not report.valid or report.css is None:
        raise SystemExit(f"the Default theme is invalid: {[i.code for i in report.errors]}")
    lines = [line for line in report.css.splitlines() if not line.startswith(("@font-face", "/* "))]
    # A cascade layer, so the active theme's (unlayered) stylesheet always wins, whatever the link order.
    body = "\n".join("  " + line for line in lines)
    return HEADER + "@layer hauskraft-fallback {\n" + body + "\n}\n"


def main() -> int:
    text = render()
    if "--check" in sys.argv[1:]:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(f"{OUT.relative_to(REPO)} is stale; run `just gen`", file=sys.stderr)
            return 1
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
