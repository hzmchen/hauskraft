#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Export the core API's OpenAPI 3.1 contract (M0S-E03-05, ADR-0010).

    python scripts/export_openapi.py            write packages/schemas/openapi/core-api.openapi.json
    python scripts/export_openapi.py --check    exit 1 if the committed file is stale
    python scripts/export_openapi.py --output F write to F instead

The app is built with the repository's plugins and built-in themes and no database, so the output depends
only on the code. Keys are sorted for stable diffs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TARGET = REPO / "packages" / "schemas" / "openapi" / "core-api.openapi.json"


def render() -> str:
    os.environ.setdefault("HAUSKRAFT_LOG_LEVEL", "WARNING")
    from hauskraft_core.app import create_app
    from hauskraft_core.settings import Settings

    settings = Settings(
        env="test",
        plugin_paths=[REPO / "plugins" / "official"],
        theme_paths=[REPO / "themes" / "builtin"],
        relay_enabled=False,
    )
    return json.dumps(create_app(settings).openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail if the committed file is stale")
    parser.add_argument("--output", type=Path, default=TARGET)
    args = parser.parse_args(argv)
    text = render()
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != text:
            print(f"{args.output} is stale; run `just gen-openapi`.", file=sys.stderr)
            return 1
        print("OpenAPI contract is current")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
