# SPDX-License-Identifier: AGPL-3.0-or-later
"""Alembic, driven from code (M0S-E04-01).

Core revisions live in ``services/core_api/migrations/versions`` on the branch ``core``. Every in-process
plugin whose manifest sets ``runtime.migrations`` contributes its own folder and branch (labelled with the
plugin id); plugin branches may depend only on core heads. ``alembic.ini`` at the repo root offers the same
for the ``alembic`` CLI.
"""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, MetaData, create_engine

from hearthos_core.plugins.manifests import discover
from hearthos_core.settings import Settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"
CORE_VERSIONS = MIGRATIONS_DIR / "versions"


def version_locations(settings: Settings) -> list[Path]:
    locations = [CORE_VERSIONS]
    for found in discover(settings.plugin_paths):
        rel = found.runtime.get("migrations")
        if found.error is None and found.runtime.get("kind") == "inprocess" and isinstance(rel, str):
            path = (found.folder / rel).resolve()
            if path.is_dir() and path.is_relative_to(found.folder.resolve()):
                locations.append(found.folder / rel)
    return locations


def target_metadata(settings: Settings) -> list[MetaData]:
    """Metadata compared by ``alembic check``: core tables plus every loaded plugin's own MetaData."""
    from hearthos_core.app import create_app
    from hearthos_core.db import models  # noqa: F401 - registers the core tables on the metadata
    from hearthos_core.db.base import metadata
    from hearthos_core.plugins.loader import plugin_metadata

    return [metadata, *plugin_metadata(create_app(settings))]


def sync_url(url: str) -> str:
    """Alembic runs synchronously; psycopg 3 serves both modes under the same URL."""
    return url


def alembic_config(settings: Settings) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("path_separator", "os")
    cfg.set_main_option("version_locations", os.pathsep.join(str(p) for p in version_locations(settings)))
    cfg.set_main_option("sqlalchemy.url", sync_url(settings.database_url).replace("%", "%%"))
    cfg.attributes["settings"] = settings
    return cfg


def upgrade(settings: Settings, target: str = "heads") -> None:
    command.upgrade(alembic_config(settings), target)


def downgrade(settings: Settings, target: str) -> None:
    command.downgrade(alembic_config(settings), target)


def check(settings: Settings) -> None:
    command.check(alembic_config(settings))


def script_heads(settings: Settings) -> set[str]:
    return set(ScriptDirectory.from_config(alembic_config(settings)).get_heads())


def database_heads(connection: Connection) -> set[str]:
    return set(MigrationContext.configure(connection).get_current_heads())


def applied_revisions(settings: Settings, db_heads: set[str]) -> set[str]:
    """Every revision reached from the database heads, following dependencies across branches.

    A plugin branch that ``depends_on`` a core revision is stored as one head in ``alembic_version``;
    the core revision it depends on counts as applied too.
    """
    if not db_heads:
        return set()
    script = ScriptDirectory.from_config(alembic_config(settings))
    return {rev.revision for rev in script.iterate_revisions(tuple(db_heads), "base")}


def heads_applied(settings: Settings, connection: Connection) -> bool:
    return script_heads(settings) <= applied_revisions(settings, database_heads(connection))


def is_at_heads(settings: Settings) -> bool:
    engine = create_engine(sync_url(settings.database_url))
    try:
        with engine.connect() as conn:
            return heads_applied(settings, conn)
    finally:
        engine.dispose()
