# A2 · ADR index (to be written in M0S-E12-02)

All in MADR format under `docs/adr/`, status `Accepted`.

| # | Title | Decision |
|---|---|---|
| 0001 | Record architecture decisions | Use MADR in `docs/adr/`; ADRs are required for any change to a seam, a schema in `packages/schemas`, or the theme contract |
| 0002 | Stack split | Python 3.13 FastAPI / SQLAlchemy 2.1 / Pydantic v2 / Postgres 16 backend and TypeScript React 19 / Vite 8 frontend, contract-first via OpenAPI 3.1 |
| 0003 | Licence split | Core (`services/**`, `apps/**`) AGPL-3.0-or-later. Everything plugin-facing MIT: SDKs, schemas, `@hauskraft/ui`, official plugins, built-in themes, theme template, HA integration. Bundled fonts OFL-1.1. MPL-2.0 considered and rejected: its extra protection adds little because a modified SDK is useless without the AGPL core, and MIT is simpler for plugin authors. REUSE-compliant SPDX headers; DCO, no CLA. Not legal advice. |
| 0004 | In-process plugin loader for M0* | Manifest-validated Python entrypoint + build-time web registry; declarative theme plugins routed to the theme registry; the same manifest later drives subprocess/container/wasm runtimes in plugin_host |
| 0005 | Auth for M0* | Local username/password, argon2id (pwdlib), server-side sessions, HttpOnly SameSite=Lax cookie, synchronizer CSRF token; `IdentityProvider` seam; OIDC in M1 |
| 0006 | Service layer + `authorize()` seam | All writes call a Policy protocol; `NoOpPolicy` in M0*, Cedar in M1+ |
| 0007 | CloudEvents + transactional outbox | CloudEvents 1.0 structured JSON in `outbox_events`, same-transaction writes, log relay; extension attributes `dataclass` and `actorid` (CloudEvents forbids underscores) |
| 0008 | Data classes as tags | 8 ordered classes on entities, events and manifests; declared, not enforced in M0* |
| 0009 | IDs | UUIDv7 generated in the app; revisit native `uuidv7()` if moving to PG18 |
| 0010 | Client generation | `@hey-api/openapi-ts` (exact pin) with the TanStack Query plugin, output in `@hauskraft/sdk-ts` |
| 0011 | TypeScript 6.0 for M0* | Stay on `~6.0` until 7.x ships a stable compiler API; re-evaluate at M1 |
| 0012 | Widget grid | react-grid-layout v2 over gridstack.js: React-native, TS types, hooks API, explicit layout state persisted per user; 12 columns in every theme |
| 0013 | Theming | Deployment-wide, data-only theme packages (plugin type `theme`, `runtime.kind: declarative`). Tokens in DTCG Format 2025.10 (light and dark files) compiled server-side to one stylesheet; component variants and limited layout options (navigation style, density, content width) as fixed enums applied via data attributes; no custom CSS or scripts; no editor; colour mode per device. Function invariance enforced by ARIA-snapshot comparison across themes and hard contrast rules. **Thresholds (proposed, confirm in the ADR):** text contrast ≥ 4.5:1, non-text ≥ 3:1, `destructive` vs `primary` OKLab distance ≥ 0.15, assets ≤ 2 MB each and ≤ 10 MB total, ≤ 8 font files, sprite ≤ 500 symbols. Theme switching any adult in M0*, owner-only once RBAC lands. Per-user/per-device overrides deferred. |
| 0014 | Test-driven development and spec-owned acceptance tests | Red/green/refactor for every story. `tests/` holds spec-owned acceptance tests and fixtures written before the code; `tests/story-status.json` marks each story red or green; red stories run as expected failures, green stories are hard gates, and CI fails when a red story is secretly green. Acceptance tests change only with the spec owner (and an ADR for contract changes). Black-box first: live API tests over HTTP, the CLI via `--json`, linters via stdin, UI via roles and accessible names (`docs/testing/ui-contract.md`). |
