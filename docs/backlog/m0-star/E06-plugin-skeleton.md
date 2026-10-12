# E06 · Plugin skeleton

**Goal:** A manifest schema, MIT SDKs, an in-process loader that also recognises declarative theme plugins, and frontend contribution discovery.
**Out of scope:** signing, registry, isolation tiers, runtime install of code plugins.
**Dependencies:** E03.

---

## Tasks plugin manifest (`plugins/official/tasks/hearthos.plugin.json`)

```json
{
  "$schema": "../../../packages/schemas/manifest/hearthos.plugin.schema.json",
  "id": "org.hearthos.tasks",
  "name": "Tasks",
  "version": "0.1.0",
  "type": ["domain", "widget"],
  "hearthos_api": "^0.1.0",
  "license": "MIT",
  "authors": [{"name": "HearthOS contributors"}],
  "source": "https://github.com/hearthos/hearthos/tree/main/plugins/official/tasks",
  "runtime": {
    "kind": "inprocess",
    "entrypoint": "hearthos_tasks.plugin:plugin",
    "api_prefix": "/tasks",
    "migrations": "backend/migrations/versions",
    "web": "@hearthos/plugin-tasks"
  },
  "capabilities": ["graph:read:Task", "graph:write:Task", "events:emit:hearthos.task.*"],
  "data_classes": {"reads": ["household"], "writes": ["household"], "emits": ["household"]},
  "config_schema": {"type": "object", "properties": {}, "additionalProperties": false},
  "contributes": {
    "widgets": [{"id": "tasks.list", "title": "i18n:tasks:widget.title", "component": "TasksWidget",
                 "default_size": {"w": 4, "h": 6}, "min_size": {"w": 3, "h": 4}}],
    "pages": [{"id": "tasks", "title": "i18n:tasks:page.title", "component": "TasksPage", "nav": true,
               "icon": "nav.tasks", "nav_order": 20}],
    "entities": [{"type": "Task", "data_class": "household"}],
    "icons": [], "tools": [], "settings": [], "commands": [], "themes": []
  },
  "subscribes": []
}
```

Theme plugins use the same manifest with `type: ["theme"]` and `runtime.kind: "declarative"` (example in spec §10.2.4 and E13-06).

---

## M0S-E06-01 · Manifest and event JSON Schemas
- **Story:** As a plugin or theme author, I want a machine-checkable manifest schema, so that mistakes fail fast.
- **AC:**
  - Given `packages/schemas/manifest/hearthos.plugin.schema.json` (`$schema` 2020-12), then the tasks manifest above and the three built-in theme manifests validate.
  - Invalid cases fail: an id that isn't reverse-DNS (`^[a-z0-9]+(\.[a-z0-9-]+)+$`), a non-SemVer version, an unknown `type` (allowed: `connector, domain, skill, workflow, widget, bridge, theme`), an unknown `runtime.kind` (allowed: `container, subprocess, wasm, inprocess, declarative`), capabilities not matching `^[a-z]+:[a-z]+(:[A-Za-z0-9.*_:-]+)?$` (the scope may contain hosts and ports, e.g. `net:egress:paperless.lan:8000`), and data classes outside the 8-value ordered enum.
  - **Theme rule:** if `type` is exactly `["theme"]`, then `runtime.kind` must be `declarative`, `capabilities` must be empty, all `data_classes` lists must be empty, `contributes.themes` must have ≥1 entry, and `contributes.widgets/pages/tools/workflows` must be absent or empty. Violations fail validation.
  - `contributes.pages[].icon` and `contributes.icons[].name` use semantic icon names (`^[a-z]+(\.[a-z0-9-]+)+$`).
- **Tech:** MIT SPDX header. `packages/schemas/README.md` documents the data-class order `public < household < personal < financial < tenant < child < health < secret`. The theme rule uses `if/then` in JSON Schema.
- **Tests:** Contract: `check-jsonschema` with valid/invalid fixtures in `packages/schemas/tests/`, including each theme-rule violation.
- **Deps:** E01-01 · **Est:** M · **Labels:** area:plugin, contract

## M0S-E06-02 · Python SDK (`hearthos_sdk`)
- **Story:** As a plugin author, I want a stable, minimal Python API, so that my plugin never imports core internals.
- **AC:** Given `hearthos_sdk`, then it exports:
  - `Plugin` (Protocol with `id`, `register(ctx) -> PluginRegistration`)
  - `PluginRegistration(router: APIRouter, metadata: MetaData | None, seed: Callable | None)`
  - `PluginContext` (Protocol: `db_session()`, `authorize(...)`, `emit(event_type, subject, data, data_class)`, `current_actor` dependency, `logger`, `config`)
  - `Actor`, `DataClass` (StrEnum, ordered), `HEARTHOS_API_VERSION = "0.1.0"`
  - `py.typed`; licence MIT.
- **Tech:** `packages/sdk-py/src/hearthos_sdk/`. Depends only on fastapi, pydantic and sqlalchemy.
- **Tests:** Unit: DataClass ordering; protocol conformance test against the core implementation.
- **Deps:** E01-02 · **Est:** S · **Labels:** area:plugin

## M0S-E06-03 · In-process plugin loader
- **Story:** As an operator, I want plugins discovered from manifests at startup, so that adding the tasks plugin requires no core code change.
- **AC:**
  - Given `HEARTHOS_PLUGIN_PATHS=plugins/official` and `HEARTHOS_THEME_PATHS=themes/builtin,/data/themes`, when the app starts, then each `*/hearthos.plugin.json` is validated and its `hearthos_api` range checked against the SDK version (npm-style ranges via `semantic_version.NpmSpec`).
  - `inprocess` plugins: the entrypoint is imported, `register(ctx)` called, and its router mounted at `/api/v1{api_prefix}` with tag = plugin short name.
  - `declarative` plugins of type `theme` are handed to the theme registry (E13-03); the loader does not import anything for them.
  - Any other `runtime.kind` is recorded with `load_error = "runtime not supported in M0*"`.
  - Prefix collisions with core (`/auth`, `/me`, `/users`, `/plugins`, `/themes`, `/theme`, `/settings`, `/activity`, `/healthz`, `/readyz`, `/dashboard`) are rejected.
  - A failing code plugin is recorded in `plugins.load_error` and makes `/readyz` 503 without crashing the app.
- **Tech:** `hearthos_core/plugins/{loader.py,context.py}`. `CorePluginContext` binds `emit()` to the outbox writer with `source = plugin id`. Undeclared `capabilities`/`data_classes` usage logs a `governance.undeclared` warning (not enforced).
- **Tests:** Unit: bad manifest, incompatible range, collision, unsupported runtime; integration: tasks plugin mounted; theme manifest routed to a registry stub.
- **Deps:** E06-01, E06-02, E03-04, E04-02 · **Est:** M · **Labels:** area:plugin

## M0S-E06-04 · Plugin registry table and API
- **Story:** As the web shell, I want to know which plugins and contributions are active, so that I render only those.
- **AC:**
  - Given loaded plugins, `GET /api/v1/plugins` returns `[{id, name, version, kind, type, enabled, contributes, load_error}]`, and the `plugins` table is upserted with `manifest_sha256`.
  - `PATCH /api/v1/plugins/{id} {enabled}` toggles a code plugin; it takes effect after restart, which the response says (`restart_required: true`). Theme plugins cannot be disabled here (themes are chosen in E13-04); the API returns 422 `use_theme_settings`.
- **Tech:** `plugins/router.py`, `plugins/repository.py`. Writes go through `authorize()` and emit `hearthos.plugin.toggled`.
- **Tests:** Integration + contract (OpenAPI regenerated).
- **Deps:** E06-03, E10-02 · **Est:** S · **Labels:** area:plugin

## M0S-E06-05 · TypeScript SDK and widget contract
- **Story:** As a plugin web author, I want typed widget and page contracts, so that the shell can render my components.
- **AC:** Given `@hearthos/sdk-ts` (MIT), then it exports:
  - `WidgetProps = { instanceId: string; pluginId: string; size: { w: number; h: number }; config: Record<string, unknown> }`
  - `PageProps = { pluginId: string }`
  - `PluginWebModule = { widgets: Record<string, React.ComponentType<WidgetProps>>; pages: Record<string, React.ComponentType<PageProps>>; locales: Record<'en'|'de', Record<string, unknown>>; icons?: Record<string, string /* default SVG */> }`
  - `definePluginWeb()`, `useHearthosClient()`, and the generated API client from `src/client/` (hey-api output).
  - UI primitives are **not** in sdk-ts; they come from `@hearthos/ui` (E13-02).
- **Tech:** `openapi-ts.config.ts`: input = the committed OpenAPI file, output = `packages/sdk-ts/src/client`, plugins `['@hey-api/typescript','@hey-api/sdk','@tanstack/react-query']`, `@hey-api/client-fetch` with `credentials: 'include'` and a CSRF interceptor.
- **Tests:** Vitest type tests (`expectTypeOf`); `just gen` is idempotent.
- **Deps:** E03-05 · **Est:** M · **Labels:** area:plugin, web

## M0S-E06-06 · Build-time web plugin registry
- **Story:** As the web shell, I want plugin web modules discovered from manifests at build time, so that adding a plugin needs no shell edits.
- **AC:**
  - Given manifests with `runtime.web`, when I run `pnpm gen:plugins`, then `apps/web/src/plugins/registry.gen.ts` is generated with `{ 'org.hearthos.tasks': () => import('@hearthos/plugin-tasks') }`.
  - Theme plugins never appear in this registry (they have no web code).
  - At runtime the shell renders a contribution only if it is in the registry and enabled in `GET /plugins`.
  - An unknown widget ID renders a "Widget unavailable" card.
- **Tech:** `scripts/gen-plugin-registry.mjs`, run by `just gen` and Vite `buildStart`. `React.lazy` + `Suspense` + an error boundary per widget.
- **Tests:** Vitest: registry generation, theme manifests skipped, unavailable fallback.
- **Deps:** E06-05 · **Est:** S · **Labels:** area:plugin, web
