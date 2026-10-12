# E07 · Tasks plugin (backend)

**Goal:** Backend of the super-simple shared task list, as the first native in-process plugin.
**Out of scope:** projects, recurrence, assignment, subtasks, labels, search, per-user permissions.
**Dependencies:** E05, E06, E10-01/02.

**Decision D3:** the list is shared. Any adult may create, edit, complete, reopen or delete any task, including tasks created by another adult. `authorize()` is where finer rules can be added in M1+.

---

## `tasks` table (plugin branch `org.hearthos.tasks`)

```text
tasks  id uuid PK (UUIDv7) | title text NOT NULL CHECK (char_length(btrim(title)) BETWEEN 1 AND 200) |
       done bool NOT NULL DEFAULT false | done_at timestamptz NULL | due_on date NULL |
       data_class text NOT NULL DEFAULT 'household' | version int NOT NULL DEFAULT 1 |
       created_by uuid NOT NULL FK users | updated_by uuid NOT NULL FK users |
       created_at timestamptz NOT NULL DEFAULT now() | updated_at timestamptz NOT NULL DEFAULT now()
       INDEX (done, created_at DESC); INDEX (due_on) WHERE due_on IS NOT NULL
```

## Tasks REST API (contract; all require a session, writes require CSRF)

| Method & path | Request | Response | Status codes |
|---|---|---|---|
| `GET /api/v1/tasks` | query `status=open\|done\|all` (default `all`), `sort=created_at\|-created_at\|due_on\|-due_on` (default `-created_at`; nulls last for due), `limit` 1–200 (default 50), `offset` ≥0 | `{items: Task[], total, limit, offset}` | 200, 401, 422 |
| `POST /api/v1/tasks` | `{title: string, due_on?: date\|null}` | `Task`, `Location` header | 201, 401, 403, 422 |
| `GET /api/v1/tasks/{id}` | — | `Task` | 200, 401, 404 |
| `PATCH /api/v1/tasks/{id}` | `{title?, due_on?: date\|null, done?: bool, version?: int}` | `Task` | 200, 401, 403, 404, 409 `version_conflict`, 422 |
| `DELETE /api/v1/tasks/{id}` | — | — | 204, 401, 403, 404 |

`Task = {id, title, done, done_at, due_on, data_class, version, created_by: {id, display_name}, updated_by: {id, display_name}, created_at, updated_at}`. Titles are trimmed. Unknown fields return 422 (`extra="forbid"`).

---

## M0S-E07-01 · Plugin package, model and migration
- **Story:** As a plugin author, I want the tasks plugin to own its table and migration, so that it proves the plugin data seam.
- **AC:**
  - Given the loader, then `hearthos_tasks.plugin:plugin` registers.
  - `alembic upgrade heads` creates `tasks` per the contract.
  - The package imports nothing from `hearthos_core` (lint-enforced). Licence MIT.
- **Tech:** `plugins/official/tasks/backend/src/hearthos_tasks/{plugin.py,models.py}`. Models use their own `MetaData` passed in `PluginRegistration`.
- **Tests:** Integration: migration and CHECK constraint.
- **Deps:** E06-03, E04-01 · **Est:** S · **Labels:** area:tasks

## M0S-E07-02 · Task service with authorize and events
- **Story:** As an adult household member, I want my task changes recorded consistently, so that the list and activity feed never disagree.
- **AC:** Given any create, update or delete, then the service calls `ctx.authorize(actor, "task.<verb>", ResourceRef("Task", id), "household", "graph:write:Task")`, writes the row, and calls `ctx.emit(...)` in the same transaction. Events:
  - `hearthos.task.created` on create.
  - `hearthos.task.completed` when `done` flips false→true (sets `done_at`).
  - `hearthos.task.updated` for other changes, including reopening (clears `done_at`); payload has `changes`.
  - `hearthos.task.deleted` with a snapshot on delete.
  - A version mismatch returns 409. A rollback leaves neither row nor event.
  - Adult B can update and delete a task created by adult A; `updated_by` and the event `actorid` record B.
- **Tech:** `service.py` (pure functions over `PluginContext`); `schemas.py` (Pydantic v2 `TaskCreate`, `TaskPatch`, `TaskOut`).
- **Tests:** Unit with a fake ctx: event type per transition, authorize spy. Integration: atomicity (force an emit failure → no row); cross-adult edit/delete.
- **Deps:** E07-01, E10-02, E03-04 · **Est:** M · **Labels:** area:tasks, governance

## M0S-E07-03 · Tasks router (CRUD, filter, sort, paginate)
- **Story:** As an adult household member, I want to list, add, edit, complete and delete tasks via the API, so that the UI can drive them.
- **AC:**
  - Given the API contract above, then every endpoint behaves exactly as tabled.
  - `status=open&sort=due_on` returns undone tasks with the earliest due date first and nulls last.
  - The OpenAPI file shows tag `tasks` and operationIds `tasks_list`, `tasks_create`, `tasks_get`, `tasks_update`, `tasks_delete`.
- **Tech:** `router.py` uses `ctx.current_actor`.
- **Tests:** Integration via `httpx.AsyncClient` (ASGI transport); contract snapshot; Schemathesis on `/tasks`.
- **Deps:** E07-02, E05-03 · **Est:** M · **Labels:** area:tasks, contract

## M0S-E07-04 · Demo fixtures for tasks
- **Story:** As a tester, I want seeded tasks, so that the dashboard isn't empty on first login.
- **AC:**
  - Given `fixtures/household/demo.json`, when the seed runs, then 3 tasks exist: "Water the plants" (open), "Take out recycling" (open, due tomorrow relative to seed time) and "Book chimney sweep" (done), created by `demo`.
  - The seed goes through the service, so it emits events, and it is idempotent by fixture key.
- **Tech:** The plugin exposes `seed(ctx, fixture)` via `PluginRegistration.seed`; invoked by the core seed command (E11-02).
- **Tests:** Integration: running the seed twice gives 3 tasks and 3 created events.
- **Deps:** E07-02 · **Est:** S · **Labels:** area:tasks, fixtures
