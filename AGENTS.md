# AGENTS.md — rules for AI coding agents (and humans) in Hauskraft

## Project in one paragraph
Hauskraft is a plugin-first, themeable household cockpit centred on Home Assistant. Core (AGPL-3.0-or-later):
`services/core_api` (FastAPI) and `apps/web` (React). Everything plugin-facing is MIT: `packages/sdk-py`,
`packages/sdk-ts`, `packages/ui`, `packages/schemas`, `plugins/official/*`, `themes/*`.
Spec: [docs/spec/hauskraft-spec-v0.2.md](docs/spec/hauskraft-spec-v0.2.md).
Current milestone: M0* — [docs/backlog/m0-star/README.md](docs/backlog/m0-star/README.md).
Testing: [docs/testing/README.md](docs/testing/README.md). Decisions: [docs/adr/](docs/adr/README.md).
Nested `AGENTS.md` files in `apps/web`, `packages/ui`, `plugins/official/tasks` and `themes` add local rules.
Do not implement anything listed as out of scope.

## How you work: red, green, refactor (non-negotiable)
1. Pick one story. Read its epic file, the spec sections it cites and the ADRs.
2. **Red.** Run its spec-owned acceptance tests in raw mode and watch them fail for the right reason:
   `python -m pytest tests --story M0S-Exx-yy` (add `--live` with the stack running) and, for UI stories,
   `HAUSKRAFT_TDD_RAW=1 pnpm --filter @hauskraft/acceptance-e2e exec playwright test --grep @M0S-Exx-yy`.
   Then write the unit/integration tests for your code and watch them fail. Commit `test(M0S-Exx-yy): red …`.
3. **Green.** Write the least code that makes every one of those tests pass. Commit `feat(M0S-Exx-yy): …`.
4. **Refactor** with everything green. Commit `refactor(M0S-Exx-yy): …`.
5. **Flip.** Set the story to `"green"` in `tests/story-status.json`, run
   `python scripts/backlog_tools.py coverage --write` and `python scripts/backlog_tools.py check`.
6. Never edit, skip or delete anything under `tests/acceptance/`, `tests/e2e/` or `tests/fixtures/` to get to green.
   If a spec-owned test looks wrong, stop and explain it in the PR.

## Setup & commands
- Toolchain: Python 3.13 (uv), Node 24 (pnpm), Docker. `just setup` once (after M0S-E01-04).
- Before the workspace exists: `python -m pip install -r tests/requirements.txt && python -m pytest tests`.
- `just check` = lint + typecheck + unit. `just acceptance` = `python -m pytest tests --strict-status`.
- `just test-int` (Testcontainers Postgres), `just contract`, `just e2e`, `just invariance`, `just themes-validate`,
  `just gen` (OpenAPI → TS client, plugin registry, theme types).
- Never hand-edit generated files: `core-api.openapi.json`, `packages/sdk-ts/src/client/**`, `routeTree.gen.ts`,
  `registry.gen.ts`, generated theme types, `docs/testing/traceability.md`.

## Architecture rules (non-negotiable)
1. Every write to a domain entity or deployment setting goes through a service function that calls `authorize()`
   first and emits exactly one CloudEvent in the same transaction. No direct ORM writes from routers.
   (Account and session bookkeeping calls `authorize()` but emits no event in M0*.)
2. Plugins import only `hauskraft_sdk` (Python) and `@hauskraft/sdk-ts` / `@hauskraft/ui` (web).
   Never `hauskraft_core` or `apps/web`.
3. API contract = OpenAPI 3.1 generated from FastAPI. Change Pydantic models → run `just gen` → commit both.
4. New tables: Alembic migration in the owning branch (core or plugin). Never `create_all()` outside tests.
5. Every entity and event carries `data_class` (the CloudEvents attribute is spelled `dataclass`; actor is `actorid`).
6. Roles: the enum has 8 values; only `adult` is creatable in M0*. Do not add role checks; route through `authorize()`.
7. Errors: problem+json with a stable `code`. User-facing strings: i18n keys in en AND de.
8. No new dependency without updating the lockfile and stating why in the PR. Respect pins (TS ~6.0).
9. Secrets never in code, logs or fixtures (except the documented demo password).

## Theming rules (non-negotiable)
10. Function is fixed, presentation is swappable. A theme may never add, remove, reorder, rename, relabel or hide
    a function. If your change makes any view's accessibility tree differ between themes, it is wrong.
11. UI code uses only `@hauskraft/ui` primitives and semantic utility classes. No colour literals, no Tailwind palette
    classes (`bg-red-500`), no arbitrary values (`p-[13px]`), no inline colour/font/spacing styles.
12. Icons only via `<Icon name="…">` with semantic names (`packages/schemas/theme/icon-names-v1.json`).
13. Navigation items come only from the `NavModel`. Renderers may differ in look, never in items, order or names.
14. Grid stays 12 columns. Density changes spacing, never structure.
15. Themes are data only: no code, no raw CSS, no external URLs. New tokens, variants or layout options need an ADR
    and a schema change in `packages/schemas/theme` first.
16. Colour mode (system/light/dark) is per device and never stored on the server. The theme is per deployment.
17. Accessible names and test hooks follow [docs/testing/ui-contract.md](docs/testing/ui-contract.md).

## Style
- Python: ruff + mypy --strict, async SQLAlchemy 2.x `Mapped[]`, Pydantic v2 `model_config = ConfigDict(extra="forbid")`.
- TS: strict, function components, TanStack Query via generated options (no ad-hoc fetch), `@hauskraft/ui` only.
- Tests next to scope: unit (no I/O), integration (DB), contract (schemas/OpenAPI), e2e and invariance (Playwright).

## PR rules
- One story per PR, title `[M0S-Exx-yy] …`, conventional commits, `git commit -s` (DCO).
- The PR shows the red commit before the green one.
- Fill the PR template: AC checklist, tests run, screenshots in all three built-in themes for UI changes.
- If an AC is ambiguous or conflicts with an ADR or the spec: stop and ask in the PR; do not invent scope.
