# SPDX-License-Identifier: AGPL-3.0-or-later
"""The ``hearthos`` command line (M0S-E05-05; ``themes`` and ``seed`` join later).

Configuration comes from the same ``HEARTHOS_*`` environment variables as the API.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Annotated

import typer
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from hearthos_core.db import migrations
from hearthos_core.policy import policy_from_settings
from hearthos_core.settings import Settings
from hearthos_core.uow import UnitOfWork
from hearthos_core.users import service
from hearthos_sdk.errors import HearthosError

app = typer.Typer(help="HearthOS administration.", no_args_is_help=True, pretty_exceptions_enable=False)
users_app = typer.Typer(help="Manage local accounts.", no_args_is_help=True)
db_app = typer.Typer(help="Database schema.", no_args_is_help=True)
app.add_typer(users_app, name="users")
app.add_typer(db_app, name="db")


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


@db_app.command("upgrade")
def db_upgrade() -> None:
    """Apply core and plugin migrations up to heads."""
    migrations.upgrade(Settings())
    typer.echo("Database is at heads.")


if __name__ == "__main__":
    app()
