# E09 · Account events & activity

**Goal:** Account and household changes are CloudEvents with closed schemas, and Activity tells the household about
them in plain language (spec §2.3, ADR 0018).
**Out of scope:** The hash-chained audit log, notifications, filtering Activity by type.
**Dependencies:** none beyond M0*.

---

## Contract: event data schemas

All in `packages/schemas/events/`, JSON Schema 2020-12, `additionalProperties: false` at every level, `$id`
`https://hauskraft.dev/schema/events/<suffix>/v1.json`. Source `dev.hauskraft.core`; subject `user/<id>` or
`setting/household`.

| Type | `dataclass` | `data` |
|---|---|---|
| `hauskraft.user.created` | personal | `{user: UserRef}` |
| `hauskraft.user.updated` | personal | `{user: UserRef, changes: {display_name?: {from, to}, role?: {from, to}}}` (at least one change) |
| `hauskraft.user.deactivated` | personal | `{user: UserRef}` |
| `hauskraft.user.reactivated` | personal | `{user: UserRef}` |
| `hauskraft.user.password_reset` | personal | `{user: UserRef}` |
| `hauskraft.user.password_changed` | personal | `{user: UserRef}` |
| `hauskraft.settings.household_changed` | household | `{changes: {name?: {from, to}, timezone?: {from, to}, locale?: {from, to}}}` (at least one change) |

`UserRef = {id (uuid), username, display_name, role ("owner" | "adult")}`, the values after the change.

## Contract: Activity summaries

| Type | en | de |
|---|---|---|
| `user.created` | `<actor> added <name> to the household` | `<actor> hat <name> zum Haushalt hinzugefügt` |
| `user.updated` | `<actor> updated the account of <name>` | `<actor> hat das Konto von <name> geändert` |
| `user.deactivated` | `<actor> deactivated <name>` | `<actor> hat <name> deaktiviert` |
| `user.reactivated` | `<actor> reactivated <name>` | `<actor> hat <name> reaktiviert` |
| `user.password_reset` | `<actor> reset the password of <name>` | `<actor> hat das Passwort von <name> zurückgesetzt` |
| `user.password_changed` | `<actor> changed their password` | `<actor> hat das eigene Passwort geändert` |
| `settings.household_changed` | `<actor> changed the household settings` | `<actor> hat die Haushaltseinstellungen geändert` |

`<actor>` is the actor's current display name, as in M0*; `<name>` is `data.user.display_name`.

---

## M1S-E09-01 · Account event schemas
- **Story:** As a future audit-log or plugin author, I want account events to have closed schemas, so that secrets
  can't slip into them and consumers can rely on their shape.
- **AC:**
  - Given the seven schemas above, then every fixture in `tests/fixtures/events/accounts/valid/` validates against
    the envelope and its data schema, and every fixture in `tests/fixtures/events/accounts/invalid/` fails its data
    schema (an extra `password` field, a `password_hash`, an empty `changes`, an unknown role, a missing `user`).
  - The envelope schema is unchanged.
- **Tech:** `packages/schemas/events/*.data.schema.json` (MIT). No code.
- **Tests:** Contract: `tests/acceptance/schemas/test_account_event_schemas.py`.
- **Deps:** — (M0* done) · **Est:** S · **Labels:** area:events, type:chore

## M1S-E09-02 · Activity summaries for account events
- **Story:** As a household member, I want Activity to say who changed which account, so that changes to who can act
  in the household are visible.
- **AC:**
  - Given account and household events in the outbox, `/activity` shows them with the summaries above in en and de;
    unknown types keep the M0* fallback.
  - `GET /activity` returns the new types with the same item shape as the M0* types.
- **Tech:** `apps/web/src/routes/_app/activity.tsx` (summary map), locale files; `activity/` in core only if the item
  shape needs a field.
- **Tests:** E2E: `tests/e2e/basics.spec.ts` step 3, `tests/e2e/members.spec.ts`. Live: `test_account_events.py`.
  Static: the M0* i18n key-parity test.
- **Deps:** E09-01 · **Est:** S · **Labels:** area:web, area:events
