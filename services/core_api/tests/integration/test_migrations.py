# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E04-01: Alembic with a core branch plus plugin branches found through plugin manifests."""

import json
import textwrap
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from testcontainers.postgres import PostgresContainer

from hearthos_core.db import migrations
from hearthos_core.settings import Settings

pytestmark = pytest.mark.integration

PROBE_REVISION = '''
"""probe plugin table"""
import sqlalchemy as sa
from alembic import op

revision = "probe_0001"
down_revision = None
branch_labels = ("org.example.probe",)
depends_on = "core@head"


def upgrade() -> None:
    op.create_table("probe_items", sa.Column("id", sa.Integer, primary_key=True))


def downgrade() -> None:
    op.drop_table("probe_items")
'''


@pytest.fixture(scope="module")
def pg() -> Iterator[str]:
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as container:
        yield container.get_connection_url()


@pytest.fixture
def probe_plugin(tmp_path: Path) -> Path:
    plugin = tmp_path / "plugins" / "probe"
    (plugin / "migrations" / "versions").mkdir(parents=True)
    (plugin / "migrations" / "versions" / "probe_0001.py").write_text(textwrap.dedent(PROBE_REVISION))
    manifest = {
        "id": "org.example.probe",
        "name": "Probe",
        "version": "0.1.0",
        "type": ["domain"],
        "hearthos_api": "^0.1.0",
        "license": "MIT",
        "authors": [{"name": "t"}],
        "source": "x",
        "runtime": {"kind": "inprocess", "entrypoint": "probe:plugin", "migrations": "migrations/versions"},
        "capabilities": [],
        "data_classes": {"reads": [], "writes": [], "emits": []},
    }
    (plugin / "hearthos.plugin.json").write_text(json.dumps(manifest))
    return plugin.parent


def _settings(url: str, plugin_paths: list[Path]) -> Settings:
    return Settings(env="test", database_url=url, plugin_paths=plugin_paths, theme_paths=[])


def _versions(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            return {row[0] for row in conn.execute(text("SELECT version_num FROM alembic_version"))}
    finally:
        engine.dispose()


def _tables(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_version_locations_include_plugin_migrations(probe_plugin: Path) -> None:
    locations = migrations.version_locations(_settings("postgresql+psycopg://x/y", [probe_plugin]))
    assert locations[0] == migrations.CORE_VERSIONS
    assert probe_plugin / "probe" / "migrations" / "versions" in locations


def test_upgrade_heads_applies_core_and_plugin_branches_and_round_trips(pg: str, probe_plugin: Path) -> None:
    settings = _settings(pg, [probe_plugin])
    migrations.upgrade(settings)
    heads = migrations.script_heads(settings)
    assert _versions(pg) == heads
    assert "probe_items" in _tables(pg)
    assert migrations.is_at_heads(settings) is True

    migrations.downgrade(settings, "base")
    assert "probe_items" not in _tables(pg)
    assert _versions(pg) == set()
    assert migrations.is_at_heads(settings) is False

    migrations.upgrade(settings)
    assert _versions(pg) == heads


def test_core_only_check_reports_no_drift(pg: str) -> None:
    settings = _settings(pg, [])
    migrations.downgrade(settings, "base")
    migrations.upgrade(settings)
    migrations.check(settings)  # raises on drift between models and migrations


def test_naming_convention_is_set() -> None:
    from hearthos_core.db.base import metadata

    assert {"ix", "uq", "ck", "fk", "pk"} <= set(metadata.naming_convention)
