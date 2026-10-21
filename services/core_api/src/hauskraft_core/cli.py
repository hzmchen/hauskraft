# SPDX-License-Identifier: AGPL-3.0-or-later
"""The ``hearthos`` command line (M0S-E05-05, ``seed`` M0S-E11-02, ``themes`` M0S-E13-09).

Configuration comes from the same ``HEARTHOS_*`` environment variables as the API.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated

import typer
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from hearthos_core.db import migrations
from hearthos_core.logging import configure_logging
from hearthos_core.policy import policy_from_settings
from hearthos_core.settings import Settings
from hearthos_core.uow import UnitOfWork
from hearthos_core.users import service
from hearthos_sdk.errors import HearthosError

app = typer.Typer(help="HearthOS administration.", no_args_is_help=True, pretty_exceptions_enable=False)
users_app = typer.Typer(help="Manage local accounts.", no_args_is_help=True)
db_app = typer.Typer(help="Database schema.", no_args_is_help=True)
themes_app = typer.Typer(help="Check and list theme packages.", no_args_is_help=True)
app.add_typer(users_app, name="users")
app.add_typer(db_app, name="db")
app.add_typer(themes_app, name="themes")


@app.callback()
def _main() -> None:
    """Logs go to stderr as JSON; only warnings and errors, so command output stays readable."""
    configure_logging("WARNING")


def _run[T](work: Callable[[UnitOfWork], Awaitable[T]]) -> T:
    settings = Settings()

    async def _main() -> T:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with UnitOfWork(
                async_sessionmaker(engine, expire_on_commit=False), policy_from_settings(settings), settings
            ) as uow:
                return await work(uow)
        finally:
            await engine.dispose()

    try:
        return asyncio.run(_main())
    except HearthosError as exc:
        typer.secho(f"error: {exc.detail}", err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from None


def _prompt_password() -> str:
    return str(typer.prompt("Password", hide_input=True, confirmation_prompt=True))


@users_app.command("create")
def users_create(
    username: Annotated[str, typer.Option(help="Login name (lowercase a-z, 0-9, '.', '_', '-').")],
    display_name: Annotated[str | None, typer.Option(help="Name shown in the UI.")] = None,
    locale: Annotated[str, typer.Option(help="en or de.")] = "en",
) -> None:
    """Create an adult account; prompts for the password."""
    password = _prompt_password()

    async def work(uow: UnitOfWork) -> str:
        user = await service.create_user(
            uow,
            service.SYSTEM_ACTOR,
            username=username,
            display_name=display_name or username.strip().capitalize(),
            password=password,
            locale=locale,
        )
        return user.username

    typer.echo(f"Created adult account {_run(work)!r}.")


@users_app.command("set-password")
def users_set_password(username: Annotated[str, typer.Option(help="Account to change.")]) -> None:
    """Set a new password for an account; prompts for it."""
    password = _prompt_password()

    async def work(uow: UnitOfWork) -> str:
        return (await service.set_password(uow, service.SYSTEM_ACTOR, username, password)).username

    typer.echo(f"Password changed for {_run(work)!r}.")


@app.command("seed")
def seed(
    if_empty: Annotated[
        bool,
        typer.Option(
            "--if-empty", help="Accepted for clarity; seeding never touches a database that already has users."
        ),
    ] = True,
    force_demo: Annotated[bool, typer.Option("--force-demo", help="Allow the demo password in production.")] = False,
) -> None:
    """Create the demo household (fixtures/household/demo.json) when HEARTHOS_SEED_DEMO is on."""
    from hearthos_core.seed import load_fixture, run_seed

    try:
        result = asyncio.run(run_seed(Settings(), load_fixture(), force_demo=force_demo))
    except HearthosError as exc:
        typer.secho(f"error: {exc.detail}", err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from None
    typer.echo(result.reason)


@db_app.command("upgrade")
def db_upgrade() -> None:
    """Apply core and plugin migrations up to heads."""
    migrations.upgrade(Settings())
    typer.echo("Database is at heads.")


@themes_app.command("validate")
def themes_validate(
    path: Annotated[Path, typer.Argument(help="Theme folder (the one with hearthos.plugin.json).")],
    strict: Annotated[bool, typer.Option("--strict", help="Treat warnings as failures.")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Print the report as JSON.")] = False,
) -> None:
    """Check a theme package. Exit 0 valid, 1 invalid (or warnings with --strict), 2 usage error."""
    from hearthos_core.themes.validate import validate_theme

    if not path.is_dir():
        typer.secho(f"error: {path} is not a theme folder", err=True, fg=typer.colors.RED)
        raise typer.Exit(2)
    report = validate_theme(path)
    if as_json:
        typer.echo(
            json.dumps(
                {
                    "theme_id": report.theme_id,
                    "path": str(path),
                    "valid": report.valid,
                    "errors": [i.as_dict() for i in report.errors],
                    "warnings": [i.as_dict() for i in report.warnings],
                },
                indent=2,
            )
        )
    else:
        for kind, issues, colour in (("error", report.errors, typer.colors.RED), ("warning", report.warnings, None)):
            for issue in issues:
                typer.secho(f"{kind:7}  {issue.code:28}  {issue.path}", fg=colour)
                typer.echo(f"         {issue.message}")
        verdict = "valid" if report.valid else "invalid"
        typer.echo(f"{report.theme_id}: {verdict}, {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    if not report.valid or (strict and report.warnings):
        raise typer.Exit(1)


@themes_app.command("list")
def themes_list() -> None:
    """Show the themes found in HEARTHOS_THEME_PATHS, whether they are valid, and which one is active (*)."""
    from hearthos_core.plugins.manifests import discover
    from hearthos_core.themes.registry import build_registry, stored_theme_id

    settings = Settings()
    registry = build_registry(
        [d for d in discover(settings.theme_paths) if d.manifest.get("type") == ["theme"]], settings.default_theme
    )

    async def stored() -> str | None:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with async_sessionmaker(engine)() as session:
                return await stored_theme_id(session)
        finally:
            await engine.dispose()

    note = ""
    try:
        requested = asyncio.run(stored())
    except Exception as exc:  # the list is still useful without a database
        requested, note = None, f"(database not reachable ({type(exc).__name__}): showing the default theme as active)"
    active = registry.resolve(requested)
    summaries = registry.summaries(active.theme_id if active else None)
    width = max((len(s.theme_id) for s in summaries), default=0)
    for summary in summaries:
        mark = "*" if summary.active else " "
        state = "valid" if summary.valid else f"invalid ({len(summary.errors)} error(s))"
        typer.echo(f"{mark} {summary.theme_id:{width}}  {summary.origin:9}  {state:22}  {summary.name}")
    if note:
        typer.echo(note)


if __name__ == "__main__":
    app()
