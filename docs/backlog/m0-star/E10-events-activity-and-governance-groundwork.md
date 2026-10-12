# E10 · Events, activity & governance groundwork

**Goal:** CloudEvents envelope schema, transactional outbox writer, log relay and activity feed.
**Out of scope:** brokers, delivery to `subscribes[]`, hash-chained audit (M1+), policy enforcement.
**Dependencies:** E04.
**UI contract:** the accessible names and test hooks in `docs/testing/ui-contract.md` are part of every UI story's AC; the spec-owned e2e tests in `tests/e2e/` rely on them.

---

## Envelope (CloudEvents 1.0.2 structured JSON; `packages/schemas/events/cloudevent.schema.json`)

```json
{
  "specversion": "1.0",
  "id": "0199f3a2-6c1e-7b8a-9d40-2f6c1a0b7e11",
  "source": "org.hearthos.tasks",
  "type": "hearthos.task.created",
  "subject": "task/0199f3a2-6c1d-7c55-8a10-3e2b9f4c0d21",
  "time": "2026-10-12T09:15:02.481Z",
  "datacontenttype": "application/json",
  "dataschema": "https://schemas.hearthos.org/events/task.created/v1.json",
  "dataclass": "household",
  "actorid": "0199f390-1111-7aaa-8bbb-cccccccccccc",
  "data": {
    "task": {"id": "0199f3a2-6c1d-7c55-8a10-3e2b9f4c0d21", "title": "Buy milk", "done": false,
             "due_on": null, "version": 1}
  }
}
```

Variants:
- `hearthos.task.updated`: `data = {task, changes: {"title": ["Buy milk","Buy oat milk"], "due_on": [null,"2026-10-13"]}}`. Reopening appears as `changes.done: [true,false]`.
- `hearthos.task.completed`: `data = {task, completed_at}`.
- `hearthos.task.deleted`: `data = {task: <last snapshot>}`.
- `hearthos.settings.theme_changed` (source `org.hearthos.core`, schema added in E13-04): `data = {from: "org.hearthos.theme.default", to: "org.hearthos.theme.hackspace"}`.
- `hearthos.plugin.toggled` (source `org.hearthos.core`): `data = {plugin_id, enabled}`.

`dataclass` and `actorid` are HearthOS extension attributes. They are spelled without underscores because CloudEvents 1.0.2 requires attribute names to consist only of lower-case letters and digits (decision D1). JSON bodies and DB columns keep `data_class`. `source` is the plugin ID (or `org.hearthos.core`), a valid URI-reference.

---

## M0S-E10-01 · Event schemas
- **Story:** As a future consumer (workflows, gateway audit), I want typed event contracts, so that I can rely on payload shapes.
- **AC:**
  - `cloudevent.schema.json` (2020-12) requires `specversion, id, source, type, dataclass` and restricts `dataclass` to the 8 classes.
  - `task.{created,updated,completed,deleted}.data.schema.json` and `plugin.toggled.data.schema.json` validate the examples above.
  - Python Pydantic models in `hearthos_sdk.events` are tested against the schemas.
- **Tech:** MIT; `check-jsonschema` in CI.
- **Tests:** Contract: examples validate; a negative case (`data_class` as attribute name) fails.
- **Deps:** E06-01 · **Est:** S · **Labels:** area:events, contract

## M0S-E10-02 · Transactional outbox writer
- **Story:** As the platform, I want every domain or settings write to append one CloudEvent in the same transaction, so that events are reliable.
- **AC:**
  - Given `ctx.emit(type, subject, data, data_class)` (plugins) or `outbox.emit(...)` (core services), then an `outbox_events` row is added to the current session with a UUIDv7 id, `source`, `actorid = current actor`, `time = now(UTC)` and a full `envelope`.
  - The envelope is validated against the schema in dev/test (`HEARTHOS_VALIDATE_EVENTS=true`).
  - Emit outside a unit of work raises.
- **Tech:** `hearthos_core/events/outbox.py`.
- **Tests:** Integration: envelope stored and schema-valid; a rollback removes it.
- **Deps:** E04-03, E03-04, E10-01 · **Est:** S · **Labels:** area:events, governance

## M0S-E10-03 · Log relay and activity feed
- **Story:** As an adult household member, I want an activity page, so that I can see who changed what.
- **AC:**
  - Given unpublished events, a background relay in core_api (lifespan task, polling every 2 s with `FOR UPDATE SKIP LOCKED`, batch 100) logs each event as `event.published` and sets `published_at`.
  - `GET /api/v1/activity?limit=50&before=<time>` returns `[{id, type, time, actor: {id, display_name}, subject, summary_key, data}]`, newest first.
  - The web `/activity` route renders localised summaries ("Alex completed 'Buy milk'", "Demo Adult switched the theme to Hackspace").
  - Built with `@hearthos/ui` primitives only (passes the invariance suite).
- **Tech:** `events/relay.py`, `activity/router.py`, `apps/web/src/routes/_app/activity.tsx`. Relay disabled with `HEARTHOS_RELAY_ENABLED=false` in unit tests.
- **Tests:** Integration: relay marks published; API order and pagination. Playwright step in the demo spec.
- **Deps:** E10-02, E08-05 · **Est:** M · **Labels:** area:events, web
