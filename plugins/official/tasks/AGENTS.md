<!-- SPDX-License-Identifier: MIT -->

# AGENTS.md: tasks plugin (`dev.hauskraft.tasks`)

Local rules on top of the [root AGENTS.md](../../../AGENTS.md). Contract: [E07](../../../docs/backlog/m0-star/E07-tasks-plugin.md) (backend) and [E09](../../../docs/backlog/m0-star/E09-tasks-ui.md) (web).

- **MIT, first-party reference plugin.** People copy it, so keep it small and idiomatic.
- **Backend imports only `hauskraft_sdk`**, never `hauskraft_core` (ruff TID251 fails the build). Everything core offers reaches you through `PluginContext`: `db_session()`, `authorize()`, `emit()`, `current_actor`, `logger`, `config`.
- **Every write** (create, update, complete, reopen, delete) goes through `service.py`: `ctx.authorize(actor, "task.<verb>", ResourceRef("Task", id), "household", "graph:write:Task")`, then the row, then exactly one `ctx.emit(...)` in the same transaction. Routers never write.
- **Events:** `hauskraft.task.created`, `.completed` (done false→true), `.updated` (everything else, incl. reopen; payload has `changes`), `.deleted` (snapshot). Data schemas live in `packages/schemas/events/`; change them only with an ADR.
- **Table and migrations** belong to the plugin branch `dev.hauskraft.tasks` under `backend/migrations/`; it may depend only on core heads. Models use the plugin's own `MetaData`. Never `create_all()` outside tests.
- **Shared list (decision D3):** any adult may edit or delete any task. Do not add per-user checks; finer rules arrive through `authorize()` in M1.
- **Scope:** title, done, optional due date. No projects, recurrence, assignees, subtasks, labels or search.
- **Web** (`web/src`) imports only `@hauskraft/sdk-ts`, `@hauskraft/ui`, `react`, `react-dom`, `react-i18next`, `@tanstack/react-query` and its own files. Use the generated `tasks*Options` / `tasks*Mutation` helpers, never ad-hoc `fetch`.
- **UI:** `@hauskraft/ui` primitives and semantic utilities only; icons via `<Icon name="…">`; accessible names exactly as in [docs/testing/ui-contract.md](../../../docs/testing/ui-contract.md); every string in `web/src/locales/{en,de}/tasks.json`.
