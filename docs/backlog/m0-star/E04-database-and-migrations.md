# E04 · Database & migrations

**Goal:** Postgres 16 schema managed by Alembic, with core tables and plugin-owned migration branches.
**Dependencies:** E03-01.

---

## Core tables (contract)

```text
users          id uuid PK (UUIDv7, app-generated) | username text UNIQUE NOT NULL (lowercased) |
               display_name text NOT NULL | password_hash text NOT NULL | role user_role NOT NULL DEFAULT 'adult' |
               locale text NOT NULL DEFAULT 'en' CHECK (locale IN ('en','de')) | is_active bool DEFAULT true |
               external_subject text NULL UNIQUE  -- OIDC seam (M1)
               data_class text NOT NULL DEFAULT 'personal' | created_at, updated_at timestamptz NOT NULL | last_login_at timestamptz
user_role      ENUM('owner','adult','teen','kid','caregiver','property_manager','tenant','guest')
sessions       id text PK  -- sha256(token) hex; raw token only in cookie
               user_id uuid FK users ON DELETE CASCADE | csrf_token text NOT NULL | created_at | last_seen_at |
               expires_at timestamptz NOT NULL | revoked_at timestamptz NULL | user_agent text | ip inet
plugins        id text PK (reverse-DNS) | version text | kind text NOT NULL  -- 'inprocess' | 'declarative'
               enabled bool DEFAULT true | manifest jsonb NOT NULL | manifest_sha256 text NOT NULL |
               loaded_at timestamptz | load_error text NULL
deployment_settings
               key text PK  -- e.g. 'theme_id'
               value jsonb NOT NULL | updated_by uuid NULL FK users | updated_at timestamptz NOT NULL
outbox_events  id uuid PK (= CloudEvent id) | type text NOT NULL | source text NOT NULL | subject text |
               data_class text NOT NULL | actor_id uuid NULL FK users | time timestamptz NOT NULL |
               envelope jsonb NOT NULL | published_at timestamptz NULL | attempts int DEFAULT 0
               INDEX (published_at) WHERE published_at IS NULL; INDEX (time DESC)
dashboard_layouts
               user_id uuid FK | dashboard_id text DEFAULT 'today' | layout jsonb NOT NULL | updated_at |
               PK(user_id, dashboard_id)
tasks          (owned by the tasks plugin, see E07)
```

Notes:
- Theme validation results are not stored in the database; the theme registry is rebuilt from disk at startup (E13-03). Only the active `theme_id` is persisted.
- Per-device colour mode is browser-only and has no table.
- A later per-user theme override would add `users.theme_id` or a `user_preferences` table; nothing here blocks that.

---

## M0S-E04-01 · Alembic setup with plugin version locations
- **Story:** As a plugin author, I want my plugin's migrations to live with the plugin, so that core and plugins evolve independently.
- **AC:**
  - Given core and the tasks plugin, when I run `alembic upgrade heads`, then the core branch (`core`) and plugin branch (`org.hearthos.tasks`) both apply.
  - `alembic check` reports no drift. A naming convention for constraints is set.
- **Tech:**
  - Alembic `~=1.20` with async `env.py` (psycopg 3). `version_locations` is built from core plus each manifest's `runtime.migrations` path.
  - The plugin branch `depends_on` the core head that creates `users`. `MetaData(naming_convention=…)`.
- **Tests:** Integration: upgrade/downgrade round-trip on Testcontainers.
- **Deps:** E03-01 · **Est:** M · **Labels:** area:db

## M0S-E04-02 · Core tables migration
- **Story:** As a developer, I want users, sessions, plugins, deployment_settings and dashboard_layouts tables, so that auth, the shell and theming have storage.
- **AC:** Given an empty DB, when migrated, then the tables, `user_role` enum, constraints and indexes match the contract above. The ORM models in `hearthos_core/db/models.py` use SQLAlchemy 2.x `Mapped[]` typing.
- **Tech:** UUIDv7 generated in Python (`uuid6` package or equivalent; Python 3.13 lacks `uuid.uuid7`), so Postgres 16 is fine.
- **Tests:** Integration: insert/select per table; enum contains all 8 roles; `deployment_settings` upsert by key.
- **Deps:** E04-01 · **Est:** S · **Labels:** area:db

## M0S-E04-03 · Outbox table migration
- **Story:** As a future workflow engine, I want a durable outbox, so that events are never lost between write and publish.
- **AC:** Given the migration, then `outbox_events` exists per the contract. A trigger rejects `DELETE`, and rejects `UPDATE` of any column except `published_at` and `attempts` (append-only).
- **Tech:** PL/pgSQL trigger `outbox_append_only()`.
- **Tests:** Integration: DELETE raises; UPDATE of `envelope` raises.
- **Deps:** E04-01 · **Est:** S · **Labels:** area:db, governance

## M0S-E04-04 · Testcontainers fixtures
- **Story:** As a coding agent, I want ready-made DB fixtures, so that integration tests are one decorator away.
- **AC:** Given `pytest -m integration`, then a session-scoped `postgres:16-alpine` container starts once, migrations run to `heads`, and each test gets a transactional `AsyncSession` rolled back after the test.
- **Tech:** `services/core_api/tests/conftest.py`, exposed as pytest plugin `hearthos_core.testing` so plugin tests reuse it. testcontainers `~=4.15`.
- **Tests:** A sample test proves isolation (row is gone in the next test).
- **Deps:** E04-01 · **Est:** S · **Labels:** area:db, type:test
