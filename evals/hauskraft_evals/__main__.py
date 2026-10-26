# SPDX-License-Identifier: MIT
"""``just eval [dataset…] [--repeat N] [--check]`` and ``just eval-compare <report> <baseline>``."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from hauskraft_evals.datasets import DatasetError, discover

REPO = Path(__file__).resolve().parents[2]
REPORTS = REPO / "evals" / "reports"


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"Set {name} (see evals/README.md).")
    return value


def _price(name: str) -> float | None:
    raw = os.environ.get(name, "").strip()
    return float(raw) if raw else None


@contextmanager
def _database() -> Iterator[str]:
    """``HAUSKRAFT_TEST_DATABASE_URL`` (a disposable database) or a fresh Testcontainers Postgres."""
    external = os.environ.get("HAUSKRAFT_TEST_DATABASE_URL")
    if external:
        yield external
        return
    from testcontainers.community.postgres import PostgresContainer

    from hauskraft_core.testing import POSTGRES_IMAGE

    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg") as container:
        yield container.get_connection_url()


def run(args: argparse.Namespace) -> int:
    try:
        datasets = discover(REPO)
    except DatasetError as exc:
        print(exc, file=sys.stderr)
        return 1
    unknown = sorted(set(args.datasets) - set(datasets))
    if unknown:
        print(f"Unknown dataset {', '.join(unknown)}; there are: {', '.join(sorted(datasets))}", file=sys.stderr)
        return 1
    chosen = [datasets[n] for n in args.datasets] if args.datasets else list(datasets.values())
    if args.check:
        cases = sum(len(d.cases) for d in chosen)
        print(f"OK: {len(chosen)} datasets, {cases} cases ({', '.join(d.name for d in chosen)}).")
        return 0

    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    from hauskraft_core.db import migrations
    from hauskraft_core.settings import Settings
    from hauskraft_evals.household import Endpoint, Household
    from hauskraft_evals.runner import EvalConfig, run_datasets

    endpoint = Endpoint(_env("HAUSKRAFT_EVAL_BASE_URL"), _env("HAUSKRAFT_EVAL_API_KEY"), _env("HAUSKRAFT_EVAL_MODEL"))
    prices = (_price("HAUSKRAFT_EVAL_PRICE_INPUT"), _price("HAUSKRAFT_EVAL_PRICE_OUTPUT"))
    judge = OpenAIChatModel(
        os.environ.get("HAUSKRAFT_EVAL_JUDGE_MODEL") or endpoint.model,
        provider=OpenAIProvider(base_url=endpoint.base_url, api_key=endpoint.api_key),
    )
    config = EvalConfig(
        model=endpoint.model,
        repeat=args.repeat,
        max_tokens=int(os.environ.get("HAUSKRAFT_EVAL_MAX_TOKENS") or 200_000),
        out_dir=args.out,
        judge_model=judge,
        prices=(prices[0], prices[1]) if prices[0] is not None and prices[1] is not None else None,
    )
    with _database() as url:
        settings = Settings(
            env="test",
            database_url=url,
            plugin_paths=[REPO / "plugins" / "official"],
            theme_paths=[REPO / "themes" / "builtin"],
            relay_enabled=False,
        )
        migrations.upgrade(settings)
        with Household(settings, endpoint=endpoint) as household:
            result = run_datasets(chosen, household, config)
    print(result.markdown_path.read_text(encoding="utf-8"))
    print(f"Report: {result.json_path}\n        {result.markdown_path}")
    if result.stopped:
        print(result.stopped, file=sys.stderr)
    return result.exit_code


def main(argv: list[str] | None = None) -> int:
    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # the report is the output
    parser = argparse.ArgumentParser(prog="just eval", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_run = sub.add_parser("run", help="run datasets against the endpoint from the environment")
    p_run.add_argument("datasets", nargs="*", help="dataset names (default: all)")
    p_run.add_argument("--repeat", type=int, default=None, help="runs per case (default: each dataset's repeat)")
    p_run.add_argument("--check", action="store_true", help="only validate the datasets; no model is called")
    p_run.add_argument("--out", type=Path, default=REPORTS, help="where reports go (default: evals/reports)")
    p_cmp = sub.add_parser("compare", help="compare a report with a baseline")
    p_cmp.add_argument("report", type=Path)
    p_cmp.add_argument("baseline", type=Path)
    args = parser.parse_args(argv)
    if args.command == "compare":
        from hauskraft_evals.report import compare

        print(compare(args.report, args.baseline))
        return 0
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
