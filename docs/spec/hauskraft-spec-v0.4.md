# Hauskraft Specification v0.4

**A Home Assistant–centred, plugin-first household cockpit**

| | |
|---|---|
| Status | Draft |
| Version | 0.4 (supersedes 0.3) |
| Date | 2026-10-24 |
| Name | Hauskraft, formerly HearthOS (D10, ADR 0015) |
| Companion docs | `docs/backlog/m2-star/` (M2* backlog), `docs/backlog/m1-star/` and `docs/backlog/m0-star/` (done), `docs/adr/` (decisions) |

**Bottom line.** Hauskraft is an AGPL-3.0, Python-backend / TypeScript-frontend standalone web app. Home Assistant (HA) is the event bus and device layer. Every household domain is a plugin that wraps an existing tool through MCP or REST, or a native module where no tool exists. All agent actions pass through one governed tool gateway (default-deny writes, human approval, spend limits, data-class routing). The dashboard is themeable: themes change how it looks, never what it does. Native code is written only where the ecosystem has real gaps: the German rental/Nebenkosten workflow, a cross-domain household graph and deadline engine, the approval inbox, the theming system and the cockpit UI itself.

---

## 0. Changes

### 0.1 Changes in v0.4 (since v0.3)

| # | Change | Sections |
|---|---|---|
| C13 | **Roadmap: an agentic harness before the capability ladder.** The milestone after M1\* is **M2\* Agentic harness**: the seams that agents and workflow automation stand on, without the full governance stack of §8.1–§8.9. Elsewhere in this spec, "M2" still means the MVP-domains milestone. | §8.0, §13.1, §14 |
| C14 | **One tool contract, MCP at the edges.** Plugins declare tools in the manifest and register them through the SDK; core keeps one tool registry that the built-in assistant uses directly. MCP becomes an adapter for outside agents and outside tools later (ADR 0019). This answers open question 14. | §5.3, §8.0, §14 |
| C15 | **Assistant on behalf of a person.** The assistant calls tools with the person's own permissions; events record the run (`agentrunid`); a gate decides allow, confirm or deny per call (ADR 0020). | §3.2, §8.0 |
| C16 | **Owner-configured model endpoint.** An OpenAI-compatible Chat Completions endpoint, set in Settings → Assistant; the API key is encrypted at rest (ADR 0021). Token usage is recorded per request and shown to owners. | §8.0, §8.9, §10.1 |
| C17 | **Skills and evals.** Skills are declarative `SKILL.md` bundles contributed by plugins (ADR 0023). The harness is measured by evals in two layers: free scripted tests in CI, real-model evals on demand (ADR 0022). | §5.2, §5.3, §8.0, §13.3 |

### 0.2 Changes in v0.3 (since v0.2)

| # | Change | Sections |
|---|---|---|
| C8 | **Roadmap: basics first.** The next milestone is **M1\* Household basics**, not the governed gateway. Capability work (gateway, policy engine, approvals, LLM routing, HA, OIDC) moves to a capability ladder that is re-planned milestone by milestone. Elsewhere in this spec, "M1" and "M1+" mean that governed-gateway milestone, not M1\*. | §13.1, §14 |
| C9 | **Two roles enabled.** `owner` and `adult`. Permissions come from a static table behind `authorize()` (ADR 0016); Cedar stays the later policy engine. | §2.1, §2.3, §8.3 |
| C10 | **Household accounts.** First-run setup in the browser (the first visitor wins, ADR 0017), members managed by owners, forced password change after a new account or reset, sessions per device. | §2.2, §2.3 |
| C11 | **Household settings.** Name, time zone and default language are deployment settings. The household time zone decides what "today" means. | §2.3, §9.1, §10.1 |
| C12 | **Account events.** Changes to members and passwords are CloudEvents shown in Activity (ADR 0018). | §2.3, §3.2 |

### 0.3 Changes in v0.2 (since v0.1)

| # | Change | Sections |
|---|---|---|
| C1 | **Licences simplified.** Core stays AGPL-3.0-or-later. Everything plugin-facing is MIT: SDKs, schemas, UI kit, official plugins, built-in themes, HA integration. MPL-2.0 dropped. | §4.2 |
| C2 | **Themeable dashboard.** New principle P7 (function fixed, presentation swappable), new `theme` plugin type, full theming system, theme threats, theming in M0*. | §1, §5, §10.2, §11, §12, §13 |
| C3 | **CloudEvents naming.** Extension attributes are spelled `dataclass` and `actorid` (CloudEvents forbids underscores). JSON bodies and DB columns keep `data_class`. | §3.2 |
| C4 | **Roadmap.** M0 replaced by **M0\***: scaffolding plus one native tasks plugin plus theming, single adult role, no third-party integrations (HA counts as third-party). HA bridge moves to M1. | §13 |
| C5 | **Shared task list.** In M0* any adult may edit or delete any task. Finer rules arrive with policy in M1+. | §13.1 |
| C6 | **Name clash recorded.** | §14 |
| C7 | **Renamed to Hauskraft** (formerly HearthOS): code namespace `hauskraft`, IDs `dev.hauskraft.*`, schemas on hauskraft.dev (ADR 0015). | all |

---

## 1. Vision, goals, non-goals, design principles

**Vision.** A household cockpit: one place where a busy family sees and steers calendar, chores, meals, shopping, kids, money, homes and rentals, relationships, projects, documents, contracts, vehicles, health and energy. An agent prepares, drafts, reconciles and reminds; humans approve anything consequential. The family can make it look the way they like without changing how it works.

**Goals**
1. **HA-centred.** HA is the hub for entities, events, notifications, presence and voice. The cockpit consumes HA and publishes back into it.
2. **Reuse-first.** Each domain wraps a best-of-breed self-hosted tool, which stays the system of record. The cockpit holds an index/cache plus only the data no tool owns.
3. **Composable and malleable.** Everything is a plugin: domains, widgets, agent skills, workflows, bridges and themes. Users rearrange dashboards and swap themes without forking.
4. **Governed agency.** Agents read broadly and write narrowly. Writes are default-deny, policy-checked, approval-gated where required, audited and verified.
5. **Local-first privacy.** Data is tagged by class at the plugin boundary. Children's, health and tenant data never leave the LAN unless an admin explicitly overrides it.
6. **Agent-implementable.** Every module has a typed contract (OpenAPI, JSON Schema, MCP tool schemas), acceptance tests and a small surface.

**Non-goals:** multi-tenant SaaS; replacing HA's automation engine, Lovelace or device integrations; autonomous checkout, payment initiation or bank transfers in v1 (agents fill carts, humans pay); a general note-taking "life OS"; a legal or tax advice engine (Nebenkosten output is a draft for landlord review); an in-app theme editor or custom CSS (v0.2).

**Design principles (normative)**
- **P1 Tool of record wins.** Conflicts resolve toward the source.
- **P2 Capabilities, not trust.** A plugin gets only what its manifest declares and the admin grants.
- **P3 Policy outside the model.** Allow/deny/approval, spend caps and data routing live in deterministic code.
- **P4 Untrusted content cannot trigger actions.** Email, document, web or tenant content is processed by a tool-less "reader" model.
- **P5 Verify, don't trust, tool results.** Every write is followed by a read-back check before it is reported as success.
- **P6 Everything exportable.** iCalendar, vCard, JSON-LD, CSV and one-command backup.
- **P7 Function is fixed, presentation is swappable.** Themes may change colours, type, shapes, component styles, icons and a small set of layout options. They can never add, remove, reorder, rename or hide functions (§10.2.2).

## 2. Personas, roles and key journeys

### 2.1 Roles (RBAC)

| Role | Typical person | Can see | Can do | Agent on their behalf |
|---|---|---|---|---|
| `owner` | Admin parent | Everything incl. audit, secrets metadata | Install plugins and themes, grant capabilities, approve any action | Full, subject to policy |
| `adult` | Co-parent/partner | All domains except data marked `private:<owner>` | Approve within spend limits, edit all domains | Writes need approval per policy |
| `teen` (13–17) | Teenager | Own tasks, calendar, lists, chores/allowance | Add to lists, complete chores, request purchases | Read own + propose only |
| `kid` (<13) | Child | Kid view: chores, schedule, rewards | Tick chores, voice "what's today" | No write tools except chore completion |
| `caregiver` | Grandparent, nanny | Time-boxed: kid schedule, allergies, emergency contacts, Baby Buddy | Log feeds/naps, add notes | None or read-only |
| `property_manager` | External Hausverwaltung | Assigned properties: tickets, contractors, meter readings | Update tickets, upload invoices | None |
| `tenant` | Rental tenant | Own unit: tickets, statements, shared documents | Open ticket, submit meter reading | None (portal non-agentic in v1) |
| `guest` | Visitor | Wi-Fi card, house manual | None | None |

M0* creates the full role enum but enables only `adult`. M1* enables `owner` and `adult` (§2.3); the other six roles stay in the enum and cannot be created. Cockpit identity is local accounts in M0* and M1*, and OIDC (built-in, or Authelia/Authentik/Keycloak) later; roles map to HA users where an HA identity is needed. `tenant` and `property_manager` are served from a separate, optionally internet-exposed **portal** surface with its own reverse-proxy route and rate limits, never the main cockpit.

### 2.2 Key journeys (acceptance-level)

1. **Weekly family briefing (Sunday 18:00).** Collects next week's calendar, chores due (Donetick), meals (Mealie), bills and contract deadlines (Actual/Firefly + Wallos + deadline engine), kid events, vehicle service due (LubeLogger) and open rental tickets. A local model summarises. Delivered as dashboard card, HA notification and optional TTS. *AC:* no `health` or `child` data in any cloud call; every item links to its source.
2. **Meal → cart → delivery.** Mealie plan → Grocy stock diff → cart proposal → Knuspr MCP / Picnic HA cart fill. *AC:* add-to-cart only; checkout stays human; cart total checked against the weekly grocery budget in policy.
3. **Rent payment reconciliation (monthly, day 5).** Bank transactions (Actual via Enable Banking, or FinTS import) matched to expected rent per lease. Missing rent creates a landlord task and a draft reminder, never sent without approval. *AC:* matching is deterministic first (IBAN + amount + reference regex); the LLM only explains ambiguous cases.
4. **Nebenkostenabrechnung prep.** The deadline engine counts down to the §556(3) BGB deadline (12 months after the billing period ends). The agent collects invoices from Paperless (tagged by property and BetrKV cost type), meter readings and prepayments, computes allocation per Umlageschlüssel (area, persons, units, consumption) and produces a draft statement plus data-quality checklist. *AC:* calculation is pure code with unit tests; the LLM only classifies invoices, with human confirmation; statements are versioned and the delivery date recorded.
5. **Contract renewal reminders.** Paperless OCR → reader model extracts `{counterparty, start, min_term, notice_period, auto_renew}` → human confirms → reminder at notice deadline minus 4 weeks → HA actionable notification (Snooze / Create cancellation task). *AC:* extraction shows page/line provenance; nothing scheduled without confirmation.
6. **Birthday and gift planning.** CardDAV/Monica → upcoming birthdays → gift ideas from notes → budget check → list item or task. *AC:* gift notes are `personal` (local by default).
7. **Renovation project tracking.** Vikunja/Plane project → linked assets (Homebox), quotes/invoices (Paperless), contractors, budget category (Actual), HA sensors. *AC:* project page aggregates via the household graph without duplicating records.
8. **Kid development and school.** Baby Buddy logs, milestones, school ICS, activities, vaccination dates. *AC:* all `child` data local-only; caregiver access expires automatically.
9. **Tenant maintenance ticket.** Portal ticket (photo + text) → reader model classifies urgency, suggests contractor → owner approves dispatch email. *AC:* ticket text is untrusted; the actor sees only typed `{category, urgency, unit_id}`.
10. **Vehicle and home maintenance.** LubeLogger reminders and Homebox/Grocy maintenance items appear in the briefing and as HA todo items.
11. **Make it ours (theming).** An adult installs a theme package (drops a folder into the themes volume), restarts, picks it in Settings → Appearance; every device shows the new look within a minute; each device keeps its own light/dark/system mode. *AC:* the accessibility tree of every view is identical before and after the switch. (From M1*, picking the household theme needs the `owner` role.)
12. **Set up our household (M1*).** A parent installs Hauskraft without demo data, opens it in the browser, names the household, picks language and time zone and creates the first account, which becomes `owner`. *AC:* no CLI step is needed; once an account exists, setup can never run again.
13. **Bring the family in (M1*).** The owner adds a partner as `adult` with a temporary password; the partner signs in, must choose their own password, and manages their own name, language, password and devices. The owner can reset a forgotten password or deactivate an account. *AC:* the household always keeps at least one active owner; every change to a member shows in Activity; no password or hash ever appears in an event, a log line or the UI.

### 2.3 Household accounts and permissions (M1*)

**First run.** While no account exists, the API reports `setup required` and the web app shows a setup wizard instead of the login page. The wizard asks for the household name, default language, time zone and the first account (display name, username, password). Submitting it creates the household settings and an `owner` account in one transaction and signs that account in. Whoever completes the wizard first becomes the owner (ADR 0017): the operation is serialised so that two concurrent visitors cannot both succeed, and every later attempt gets 409 `setup_done`. The demo seed (`HAUSKRAFT_SEED_DEMO`) is the only other way to fill an empty database; the CLI can still create accounts at any time.

**Permissions (normative for M1*).** Every write still goes through `authorize()` (ADR-0006). The M1* policy is a static role table (ADR 0016); a denied action returns 403 `policy_denied` and leaves no row and no event.

| Action | `owner` | `adult` |
|---|---|---|
| Tasks: create, edit, complete, delete any task (shared list, D3) | yes | yes |
| Own dashboard layout, own profile (display name, language), own password, own sessions | yes | yes |
| Read household settings (name, time zone, default language) | yes | yes |
| Change household settings | yes | no |
| Change the household theme | yes | no |
| Enable or disable plugins | yes | no |
| List members; add, edit, deactivate, reactivate a member; reset a member's password | yes | no |

**Account lifecycle.**
- Usernames are fixed after creation; display names can change.
- Owners add members with a role (`owner` or `adult`) and a temporary password. A new account, and an account whose password an owner has reset, must choose a new password at the next sign-in. Until then, the API answers every other authenticated request with 403 `password_change_required`.
- A member changes their own password by giving the current one. This ends their other sessions; the current one stays.
- Deactivating an account ends all its sessions at once and blocks sign-in (403 `account_deactivated`, given only after a correct password, so the response reveals nothing to someone without it). Accounts are never deleted in M1*, so tasks and Activity keep their authors. Owners can reactivate an account.
- The household always has at least one active `owner`: demoting or deactivating the last one fails with 409 `last_owner`.
- A member sees their own sessions (device description, created, last seen, which one is current), can end any of them and can sign out everywhere. IP addresses are stored for rate limiting but not shown.
- Recovery when no owner can sign in: the CLI (`hauskraft users set-password`) on the server.

**Household settings.** `household.name`, `household.timezone` (an IANA name) and `household.locale` (default language for new members) are deployment settings (§9.1). The household time zone decides what "today" means for due dates on every device. The name appears in the browser title.

**Account events.** Account changes are domain writes (AGENTS.md rule 1): each emits exactly one CloudEvent from `dev.hauskraft.core` with `dataclass` `personal` (ADR 0018). The events are `hauskraft.user.created`, `hauskraft.user.updated` (display name or role), `hauskraft.user.deactivated`, `hauskraft.user.reactivated`, `hauskraft.user.password_reset` (by an owner) and `hauskraft.user.password_changed` (by the member). Household settings changes emit `hauskraft.settings.household_changed` with `dataclass` `household`. Language preference changes and session bookkeeping (sign-in, sign-out, ending sessions) call `authorize()` but emit no event. Event data never contains a password, a hash, a session ID or an IP address.

## 3. System architecture

### 3.1 Layers and components

```
┌──────────────────────────── Clients ─────────────────────────────┐
│ Cockpit SPA/PWA (adults/teens/kids) │ Wall/kiosk │ Tenant portal │
│        ▲ active theme (CSS + assets) applied by the shell         │
└───────────────┬──────────────────────────────────┬───────────────┘
                │ HTTPS + WebSocket (cockpit API)  │ (separate route)
┌───────────────▼──────────────────────────────────▼───────────────┐
│ core-api (FastAPI): auth/RBAC, dashboards, graph API, approvals, │
│                     theme registry + compiler                    │
├───────────────┬───────────────┬───────────────┬──────────────────┤
│ plugin-host   │ agent-harness │ workflow-     │ ha-bridge         │
│ (manifests,   │ (Pydantic AI; │ engine (DBOS; │ (WS client to HA; │
│ grants, iso-  │ reader/actor; │ schedules;    │ event ingest;     │
│ lation tiers) │ MCP client)   │ approval waits│ service calls)    │
├───────────────┴───────┬───────┴───────────────┴──────────────────┤
│ tool-gateway (MCP): tool registry; Cedar policy; approvals;       │
│ rate/spend ledger; audit emitter; result verification             │
├───────────────────────┼──────────────────────────────────────────┤
│ llm-router (LiteLLM): data_class → local (Ollama/llama.cpp) or    │
│ cloud; budgets per key                                            │
├───────────────────────┴──────────────────────────────────────────┤
│ data: Postgres 16 + pgvector; object store; Redis optional        │
│ observability: OTel → Langfuse/Phoenix + Grafana/Loki; secrets:   │
│ SOPS/age or OpenBao/Vault                                         │
└──────────────────────────────────────────────────────────────────┘
   ▲ MCP/REST                         ▲ WebSocket/REST/MCP
 Domain tools (Mealie, Grocy, Actual,  Home Assistant + hauskraft
 Paperless, Vikunja, Donetick, …)      custom integration
```

**Component contracts**
- `core-api`: REST + WebSocket; OpenAPI 3.1 is the contract. Owns users/roles, dashboards, approvals, graph read API, deployment settings and the theme registry/compiler.
- `plugin-host`: loads manifests, verifies signatures, presents capability-grant UI, supervises plugin processes, routes plugin traffic through the gateway. (M0*: an in-process loader inside core-api; declarative themes are handled by the theme registry.)
- `agent-harness`: agent definitions (briefing, planner, reconciler, librarian, concierge); enforces the reader/actor split; calls tools only via `tool-gateway`.
- `workflow-engine`: durable scheduled and event-triggered workflows with approval waits (DBOS, §4).
- `tool-gateway`: single choke point for every tool call by agents, workflows or UI automations: policy, audit, verification.
- `llm-router`: LiteLLM proxy with per-data-class model groups.
- `ha-bridge`: persistent HA WebSocket subscription, entity cache, event fan-out, service-call client.
- `hauskraft` HA custom integration (Python, separate repo or `integrations/`): exposes cockpit entities/services/events and an LLM API back into HA.

### 3.2 Internal event bus
Postgres `LISTEN/NOTIFY` plus an outbox table in v1 (NATS optional later). Envelope: CloudEvents 1.0 structured JSON with `type` like `hauskraft.lease.rent_missing`, `source` = plugin id, `subject` = graph node id, and two Hauskraft extension attributes:
- `dataclass`: the event's data class (spelled without underscore because CloudEvents attribute names may contain only lower-case letters and digits),
- `actorid`: the acting user or agent.

From M2\*, an event caused by an assistant run also carries `agentrunid`, the run's id; `actorid` stays the person on whose behalf the run acted (ADR 0020).

JSON bodies, DB columns and manifests keep the readable `data_class`. HA events are mirrored as `ha.state_changed` / `ha.event.<type>`.

### 3.3 Deployment topology
- **Primary:** Docker Compose: `core-api`, `web`, `plugin-host`, `agent-worker`, `gateway`, `litellm`, `postgres`, optional `ollama` and `langfuse`. Domain tools run in their own compose projects, referenced by URL. A `themes` volume holds third-party theme packages.
- **Optional HA add-on:** single container bundling core + gateway with SQLite-backed DBOS; HA ingress for admin, direct port for the PWA.

| Tier | Hardware | Runs | LLM strategy |
|---|---|---|---|
| S | Raspberry Pi 5 8 GB / N100 | Core, gateway, Postgres | Cloud only for `public`/`household`; sensitive features degrade to non-LLM code paths |
| M | Mini PC 32–64 GB, iGPU | + 7–14B local models | Local for sensitive extraction; cloud for non-sensitive planning |
| L | GPU box 16–24 GB VRAM | + 20–32B models, local embeddings, Whisper | Local for nearly everything; cloud opt-in |

**Network rule:** Ollama/llama.cpp bind to the Docker network only, never 0.0.0.0. SentinelOne SentinelLABS and Censys found about 175,000 publicly reachable Ollama hosts in 130 countries (scans Oct 2025–Jan 2026; The Hacker News, 29 Jan 2026).

## 4. Tech stack decision and licences

### 4.1 Language split: Python backend, TypeScript frontend

| Concern | Python | TypeScript | Decision |
|---|---|---|---|
| HA ecosystem (custom integration must be Python) | Native | WS only | **Python** |
| Agent framework with durable HITL | Pydantic AI: durable execution on Temporal, DBOS, Prefect, Restate; deferred tools with `requires_approval`, `ApprovalRequiredToolset` for MCP toolsets | Mastra, Vercel AI SDK | **Python (Pydantic AI)** |
| German banking | python-fints (LGPL-3.0), Geldstrom (pure-Python FinTS 3.0) | Few maintained Node FinTS libs | **Python** |
| Web UI, widgets, theming, MCP Apps rendering | Weak | Native | **TypeScript** |
| MCP SDKs | Official | Official | Both |

**Backend.** Python 3.13, FastAPI, SQLAlchemy 2 + Alembic, Pydantic v2, DBOS, Pydantic AI, LiteLLM proxy, MCP Python SDK.

**Frontend.** React 19 + Vite + TypeScript, TanStack Router/Query, shadcn/ui (Radix + Tailwind v4) packaged as `@hauskraft/ui`, react-grid-layout, Workbox PWA (later), `home-assistant-js-websocket` for direct entity subscriptions (M1+). React over SvelteKit for agent-implementability: coding agents have the deepest React/shadcn corpus, shadcn's CSS-variable theming maps directly onto theme tokens, and MCP Apps examples are predominantly React/iframe-based. SvelteKit remains the credible alternative.

**Why DBOS as core engine.** DBOS is a library, not a cluster; its system database can be Postgres or SQLite, Pydantic AI integrates it natively, and its durable `recv/send` maps directly to "wait for approval". Temporal is the power-user upgrade path. **n8n remains a supported plugin** (trigger n8n workflows as tools, receive webhooks) but not the governed spine, because of its fair-code licence and separate auth model.

**Policy engine.** Cedar (Apache-2.0, typed schema, analysable, embeddable via `cedarpy`) over OPA/Rego: household policies are small, role- and attribute-based, and benefit from schema validation.

**MCP gateway choice.** Implement a thin **Hauskraft gateway** in Python, since it must understand data classes, household roles, spend and approvals. Keep wire compatibility so users can front it with agentgateway or IBM ContextForge for federation. Portero's allow/deny/require-approval model is the conceptual template.

### 4.2 Licences

| Part | Paths | Licence | Reason |
|---|---|---|---|
| Core server and web app | `services/*`, `apps/web` | **AGPL-3.0-or-later** | Network service: hosted forks must share improvements. Matches neighbours (Plane CE, Monica, Homebox, Vikunja). |
| Plugin-facing packages | `packages/sdk-py`, `packages/sdk-ts`, `packages/ui`, `packages/schemas` | **MIT** | Plugins import these. An AGPL SDK would arguably make every plugin AGPL. |
| Official plugins | `plugins/official/*` | **MIT** | Reference implementations people copy. |
| Built-in themes | `themes/builtin/*` | **MIT** (theme data); bundled fonts **OFL-1.1**; icon packs under their own permissive licences (e.g. Lucide ISC, Pixelarticons MIT) | Copyable starting points for theme authors. |
| HA custom integration | `integrations/ha-hauskraft` | **MIT** | Plugin-facing; HA custom integrations may use any licence. |
| Acceptance suite, scripts, docs | `tests/`, `scripts/`, `docs/` | **MIT** | Reusable by plugin and theme authors. |
| Third-party plugins and themes | elsewhere | Author's choice | — |

**Why MIT and not MPL-2.0 for the plugin-facing parts.** MPL-2.0 would additionally force anyone who modifies the SDK files and distributes them to publish those changes. That protection adds little here: a modified SDK is useless without the core, and the core is AGPL. MIT keeps the project at two licences and is the most familiar choice for plugin authors.

**Licence boundary (normative)**
- Out-of-process plugins (container, subprocess, WASM) and declarative themes are separate works and may use any licence.
- In-process plugins may import only the MIT packages (`hauskraft_sdk`, `@hauskraft/sdk-ts`, `@hauskraft/ui`), never core internals (lint-enforced). MIT code combines with the AGPL core without conflict, so official in-process plugins are fine. Whether a closed-source third-party plugin may run in-process is legally unsettled; the project recommends out-of-process runtimes for non-open plugins and documents this in `LICENSING.md`.
- Widgets in sandboxed iframes are separate works. Plugin web code bundled into the core SPA build is distributed as part of the AGPL web app while keeping its own MIT licence.
- Contributions use DCO sign-off, no CLA. REUSE-compliant SPDX headers everywhere. This is not legal advice.

## 5. Plugin system specification

### 5.1 Lessons applied
- **HA integrations:** declarative `manifest.json`, UI config/options flows, diagnostics, quality scale.
- **VS Code / Backstage / Grafana:** typed, lazy-loaded *contribution points*; VS Code colour themes are a contribution type, which Hauskraft mirrors with `contributes.themes`.
- **Browser extensions / Deno:** explicit permission lists shown at install, revocable.
- **Obsidian / WordPress:** cautionary. Full-access in-process plugins and code-carrying themes produce supply-chain risk (cf. ClawHub). Default to out-of-process; themes are data only.
- **MCP:** tools/resources/prompts as the universal agent contract. MCP Apps (SEP-1865, extension id `io.modelcontextprotocol/ui`, stable 2026-01-26) defines `ui://` resources rendered in mandatory sandboxed iframes and lets the host pass its theme and CSS variables to the view; adopted as the third-party widget contract.
- **Extism/WASM:** host-granted capabilities via manifest (`allowed_hosts`, `allowed_paths`, memory limits, `timeout_ms`, content hash), copied for the WASM tier.

### 5.2 Plugin types

| Type | Purpose | Runtime | Example |
|---|---|---|---|
| `connector` | Wrap an existing tool's API/MCP; sync to graph; expose tools | Container or subprocess | `actual`, `paperless`, `knuspr` |
| `domain` | Native module where no tool exists | In-process via SDK, or container | `tasks`, `rentals`, `deadlines` |
| `skill` | Prompt + tool bundle + eval set | Declarative + optional code | `weekly-briefing` |
| `workflow` | Durable workflow | DBOS via SDK | `rent-reconciliation` |
| `widget` | UI card/page | Bundled component (first-party) or sandboxed iframe (MCP Apps) | `rent-status-card` |
| `bridge` | HA or channel bridge | Python | `signal-notify` |
| `theme` | Visual theme for the whole cockpit (§10.2) | **Declarative only** (data + assets, no code) | `dev.hauskraft.theme.hackspace` |

### 5.3 Manifest schema (`hauskraft.plugin.json`, JSON Schema 2020-12)

Required: `id` (reverse-DNS), `name`, `version` (SemVer), `type[]`, `hauskraft_api` (semver range), `license` (SPDX), `authors[]`, `source`, `runtime` `{kind: container|subprocess|wasm|inprocess|declarative, …}`, `capabilities`, `data_classes` `{reads, writes, emits}`.

Optional:
- `config_schema` (rendered as a config flow) plus separately declared `secrets[]`.
- `contributes`: `widgets[]` `{id, title, component | resource: "ui://…", default_size, min_size, roles}`, `pages[]`, `tools[]`, `skills[]`, `workflows[]`, `entities[]` (graph node types with JSON-LD context), `ha_entities[]`, `settings[]`, `commands[]`, `icons[]` (semantic icon names a plugin introduces, with a default SVG), `themes[]` `{id, file: "theme.json"}`.
- `subscribes`: CloudEvents types, e.g. `ha.state_changed:sensor.water_meter_*`.
- `tool_annotations`: `read_only`, `destructive`, `idempotent`, `open_world` (aligned with MCP and HA 2026.10's `llm.ToolAnnotations`). Undeclared tools are treated as destructive, write and open-world.
- **Tools and skills (M2\*, ADR 0019, ADR 0023).** Each `contributes.tools[]` entry has `name` (`<plugin>.<verb>`, e.g. `tasks.create`; sent to models as `tasks_create`, because function names may not contain dots), `description` (English, written for models), `annotations`, `data_class`, `permission` (the action in the permission table) and `agent` (the author's switch: `false` keeps the tool away from agents; default `true`). The code registers the same tools through `hauskraft_sdk.tools.ToolSpec`, with Pydantic input and output models; core refuses to load a plugin whose manifest and code disagree. `contributes.skills[]` entries are `{id, path}` pointing at a `SKILL.md`, and `contributes.agent_guidance` is a short English text (at most 600 characters) that the system prompt includes while the plugin's tools are offered.
- `verification`: per write tool, a `verify` tool + JSONPath assertion run by the gateway after the write.
- `i18n`, `icons`, `min_ha_version`, `signing` `{sigstore_bundle | minisign_pubkey}`.

**Theme plugin rules:** a plugin whose `type` is exactly `["theme"]` must use `runtime.kind: "declarative"`, declare no capabilities and no data classes, and contribute at least one `themes[]` entry. A theme plugin cannot contribute tools, widgets, pages or workflows.

### 5.4 Capability model
Scoped strings, granted at install, revocable, enforced by gateway and plugin-host:
- `net:egress:<host>` (WASM via Extism `allowed_hosts`; containers via per-plugin network + egress proxy)
- `ha:read:<entity-glob>`, `ha:call:<domain>.<service>`, `ha:event:fire:<type>`
- `graph:read:<node-type>[@data_class]`, `graph:write:<node-type>`
- `files:read|write:<bucket>`, `llm:invoke:<data_class>`, `notify:<channel>`, `secrets:<name>`
- `events:emit:<type-glob>`
- `money:propose`; `money:execute` (**reserved; not grantable in v1**)
- `portal:expose` (owner-only grant, warns about internet exposure)

Themes receive no capabilities. M0* records capabilities but does not enforce them.

### 5.5 Data classification tags
`public` < `household` < `personal` < `financial` < `tenant` < `child` < `health` < `secret`. Every graph node, tool result and event carries the max class of its inputs (taint propagates). The routing table in §8.5 decides which model may see each class. M0* tags but does not enforce.

### 5.6 Lifecycle and isolation
`discover → verify signature/digest → show capabilities & data classes → admin grant → config flow → health check → enabled → upgrade (new capabilities require re-grant) → disabled → uninstall (export/purge choice)`.

Isolation tiers (default = most isolated that works):
1. **Declarative**, no code: skills, themes.
2. **WASM** (Extism): transforms, parsers, small connectors.
3. **Container** (default for connectors): per-plugin network, read-only rootfs, no Docker socket, egress via allowlisting proxy, resource limits.
4. **In-process**: first-party or "trusted" tier only, MIT SDK surface only. (M0*: the only code tier implemented.)

### 5.7 Registry, signing, versioning, testing
- **Registry:** Git-based index of manifests + digests with tiers `official`, `verified` (reviewed, signed, conformance CI), `community` (author-signed, install warning). Remote MCP servers registered by URL with OAuth metadata. Themes are listed in the same registry.
- **Signing:** Sigstore keyless for images, WASM and theme archives; Minisign offline. Unsigned artifacts refused unless the owner enables developer mode. (Not in M0*: local folders only.)
- **Versioning:** SemVer'd plugin API and theme schema; deprecations announced two minor versions ahead.
- **Testing:** `hauskraft-plugin-kit` (pip + npm) with mock core, recorded HA fixture, MCP conformance tests (schemas, annotations, verify hooks), widget sandbox runner and a CI action. Connectors ship a docker-compose fixture of their upstream tool. Themes are tested with `hauskraft themes validate` plus the function-invariance suite (§10.2.2).

### 5.8 Example manifest (connector)

```json
{
  "$schema": "https://hauskraft.dev/schema/plugin/1.0.json",
  "id": "dev.hauskraft.connector.paperless",
  "name": "Paperless-ngx",
  "version": "0.3.0",
  "type": ["connector", "widget"],
  "hauskraft_api": ">=1.0 <2.0",
  "license": "MIT",
  "authors": [{ "name": "Hauskraft contributors" }],
  "source": "https://github.com/hzmchen/plugin-paperless",
  "runtime": { "kind": "container", "image": "ghcr.io/hauskraft/plugin-paperless", "digest": "sha256:…" },
  "config_schema": { "type": "object", "required": ["base_url"],
    "properties": { "base_url": { "type": "string", "format": "uri" } } },
  "secrets": ["paperless_api_token"],
  "capabilities": ["net:egress:paperless.lan:8000", "graph:write:Document",
    "graph:read:Property", "llm:invoke:financial", "notify:inbox"],
  "data_classes": { "reads": ["financial", "tenant", "health"], "writes": ["financial"],
    "emits": ["financial", "tenant", "health"] },
  "subscribes": ["hauskraft.deadline.created"],
  "contributes": {
    "tools": [
      { "name": "paperless.search", "annotations": { "read_only": true, "open_world": false } },
      { "name": "paperless.tag_document",
        "annotations": { "read_only": false, "destructive": false, "idempotent": true },
        "verify": { "tool": "paperless.get_document", "assert": "$.tags[*] contains input.tag" } }
    ],
    "widgets": [ { "id": "inbox", "title": "Document inbox", "resource": "ui://paperless/inbox",
      "default_size": { "w": 4, "h": 4 }, "roles": ["owner","adult"] } ],
    "entities": [ { "type": "Document", "jsonld": "https://schema.org/DigitalDocument" } ]
  },
  "signing": { "sigstore_bundle": "paperless-0.3.0.sigstore.json" }
}
```

A theme manifest example is in §10.2.4.

## 6. Domain plugin catalogue

Status as of October 2026. "Official" means published by the tool's own maintainers.

| Domain | First-choice tool (licence) | Alternatives | HA integration | MCP server | Plugin adds / native gaps | Data class |
|---|---|---|---|---|---|---|
| Calendar | Radicale / Baïkal (CalDAV) + HA calendars | Nextcloud | Core CalDAV + local calendar | Community | Family overlay, role visibility, school ICS; gap: cross-person conflict detection | household/child |
| Tasks (simple, shared) | **Native `tasks` plugin** (M0*) | — | Publishes todo (M1+) | Native (M1+) | Proves the plugin skeleton; stays the lightweight default list | household |
| Tasks & projects (rich) | **Vikunja** (AGPL-3.0) | **Plane** CE (AGPL-3.0, official MCP), Kanboard, Planka, Leantime, OpenProject | Community HACS | **Vikunja: official, built in from v2.7.0 (2 Oct 2026)** | Project pages linking assets/docs/budget; gap: cross-tool aggregation | household |
| Chores | **Donetick** | Grocy chores | **Official** integration + add-on | Community (bibiwan/mcp_donetick) | Kid view; gap: allowance ledger | household/child |
| Reminders & deadlines | Native `deadlines` + HA todo | — | Publishes todo/calendar | Native | **Core gap:** unified deadline engine | inherits |
| Meals | Mealie | Tandoor | Core | Several community | Planner widget, pantry diff | household |
| Shopping/ordering | Knuspr MCP, Picnic HA | dm (search-only MCP) | Picnic core | Knuspr official | Cart proposal + budget policy; gap: retailer abstraction | financial |
| Pantry | Grocy (MIT) | — | Community | Many community | Stock diff, expiry alerts | household |
| Kids | **Baby Buddy** (BSD-2-Clause) | — | Community HACS | **Official babybuddy-mcp** | **Gap:** milestones/school/activities module | child |
| Finance | **Actual Budget** (MIT) | **Firefly III** (AGPL), **Sure** (AGPL fork of archived Maybe Finance), Beancount/Fava, GnuCash | Community | Many community (s-stefanov/actual-mcp; Firefly: yakupemreyerli with separate read/write/delete scopes and write preview) | Rent matching, budget-aware policies; gap: reconciliation rules | financial |
| Bank access (DE) | Actual + **Enable Banking** (experimental in 26.6.0) | **FinTS** via python-fints/Geldstrom; CSV/CAMT | — | — | Provider abstraction, consent-expiry alerts; gap: **FinTS bridge** | financial |
| Investments | Ghostfolio (AGPL) | Wealthfolio | Community | Community | Net-worth widget | financial |
| Own home | **Homebox** (AGPL; v0.26.x active) + Grocy batteries/chores + HA Energy | — | Community HACS | Community (homebox-mcp) | Asset↔document↔warranty links; gap: property/asset graph | household/financial |
| Rentals | **Native `rentals` plugin** | NebenkostenFix (Python/Flask; BetrKV/HeizkostenV/CO2KostAufG; 1–15 units), Mibakus (GPLv3, desktop), OpenProperty (MIT, US-centric) | Publishes entities | Native | **Biggest gap:** tenants, leases, rent ledger, Nebenkosten, tickets, contractors, portal | tenant/financial |
| Meter readings | HA sensors (incl. AI-on-the-edge-device) | Manual portal entry | Core | HA MCP Server | Snapshots at period boundaries; gap: reading audit trail | household/tenant |
| Personal CRM | CardDAV + **Monica** (AGPL), with caution | Twenty (business CRM) | — | Community | Birthdays, gifts, cadence; gap: thin PRM layer | personal |
| Documents | **Paperless-ngx** (GPL-3.0; v3.3.0, 6 Oct 2026) | — | **Core** `paperless_ngx` | Community only | Classification, deadline extraction with provenance | inherits |
| Subscriptions/contracts | **Wallos** (≥5.0 API) | Native contracts | Community | Community (weltonfelix, mkpoli) | Gap: notice-period engine | financial |
| Vehicles | **LubeLogger** | Hammond | Community HACS | None confirmed | Service due in briefing; EV charging → fuel log | household |
| Health | **No safe default** (Fasten OnPrem archived 18 Jul 2026) | YourPHR (unproven), Paperless `health` tag | — | — | Gap: minimal local-only health log | health |
| Energy/utilities | HA Energy dashboard | — | Core | HA MCP Server | Gap: cost allocation to units | household/tenant |

**Cautions**
- **Monica:** latest tag is the v5.0.0-beta.5 pre-release from April 2025, with little main-branch activity since. Make CardDAV the contacts system of record and keep PRM extras in the cockpit graph.
- **Focalboard** standalone is unmaintained: excluded.
- **Maybe Finance** is archived; its fork **Sure** is active but US-oriented (second tier).
- **GoCardless Bank Account Data** stopped accepting new signups (Actual's docs: from July 2025); new installs use Enable Banking or FinTS.
- **FinTS** requires a free **product registration** with Die Deutsche Kreditwirtschaft. Hauskraft does *not* ship a shared product ID; the user registers, the setup wizard explains it; read-only, no payment initiation.

## 7. Home Assistant integration specification (two-way, M1+)

### 7.1 Cockpit consumes HA (`ha-bridge`)
- **Transport:** HA WebSocket API (`subscribe_events`/`subscribe_entities`, `call_service`, `get_states`, registries); REST only for history/statistics bulk reads.
- **Auth:** dedicated HA **non-admin user** "hauskraft" with a long-lived token in the secret store; admin token opt-in only for registry writes. The PWA may hold the user's own HA OAuth token for direct subscriptions to entities they may see.
- **Consumed surfaces:** entities/areas/floors/labels (→ graph `Place`, `Asset`), `todo.*`, `calendar.*`, `notify.*` and mobile-app actionable notifications, `event` entities, `person.*`, Energy/statistics, Assist (`conversation.process`).
- **HA MCP Server:** the agent reaches HA's official MCP Server through the gateway for device control; HA's exposed-entity scoping remains, cockpit policy adds a layer.
- **M0*:** only a `HomeAssistantBridge` protocol with a `NullBridge` (no network).

### 7.2 Cockpit exposes to HA (`hauskraft` custom integration, HACS, MIT)
- **Config flow:** URL + OAuth client (cockpit as provider) or API key; options flow selects domains to publish.
- **Entities:** `sensor.hauskraft_pending_approvals`, `sensor.hauskraft_next_deadline`, `sensor.hauskraft_rent_status_<unit>`, `sensor.hauskraft_budget_<category>_remaining`, `binary_sensor.hauskraft_agent_healthy`, `todo.hauskraft_<list>`, `calendar.hauskraft_deadlines`, `event.hauskraft_*`.
- **Actions:** `hauskraft.approve` / `hauskraft.reject`, `hauskraft.run_workflow`, `hauskraft.ask`, `hauskraft.log_meter_reading`, `hauskraft.add_to_cart_proposal`.
- **Actionable approvals:** pushed via the HA mobile app with APPROVE/REJECT; the integration handles `mobile_app_notification_action` and calls back. The responding HA user must map to a cockpit role with sufficient rights; out-of-band PIN confirmation above a configurable amount.
- **LLM API registration:** register a Hauskraft LLM API via `llm.async_register_api` and contribute tools through an `llm.py` platform, using HA 2026.10's `llm.ToolResult` with declared `integration` and `llm.ToolAnnotations`. HA serves every registered LLM API over its MCP Server. **Only read-only and proposal tools are exposed this way**; write tools stay behind the Hauskraft gateway so policy cannot be bypassed via HA.

### 7.3 Direction-of-truth rules
HA is truth for device state, presence and energy. The cockpit is truth for approvals, deadlines, rentals, graph, dashboards and theme, mirrored into HA as entities where useful. HA todo lists from other integrations (Picnic cart, Mealie list) are linked, not duplicated. HA frontend themes and Hauskraft themes are independent; an HA-theme importer is a possible later tool (§14).

## 8. Agent harness and governance specification (M1+)

### 8.0 The M2\* harness (implemented first)
M2\* builds the parts of this section that everything later stands on, and nothing more. §8.1–§8.9 stay the direction; each deferred item names its seam in `docs/backlog/m2-star/README.md` § Deferred.

- **One assistant, Pydantic AI, one endpoint.** The owner sets an OpenAI-compatible **Chat Completions** endpoint (base URL, model, API key) in Settings → Assistant. Settings are keyed by purpose (`chat` now; `transcription`, `speech` and more models later). The key is encrypted at rest with AES-GCM under a key derived from `HAUSKRAFT_SECRET_KEY`; the API never returns it (ADR 0021).
- **Tool registry.** Core collects every plugin's tools (§5.3) and selects a small set per run: only tools the person's role permits, the owner has not switched off, whose data class the endpoint may see (the ceiling defaults to `household`; full routing per §8.5 comes later), and that the running skill allows (ADR 0019).
- **On behalf of a person.** Tools run with the person's permissions through the plugin's normal service functions, so `authorize()` and one event per write hold. Events carry `agentrunid`; Activity says "Mia via assistant …" (ADR 0020).
- **Gate.** One function decides each call: `allow`, `confirm` or `deny`. In M2\*: tools outside the selected set are denied, `destructive` tools need confirmation in the chat, everything else is allowed. Reversible actions offer Undo instead of a question. The gate sees the run kind, channel and history, so a later risk classifier ("auto mode"), schedules (confirm becomes an approval request, §8.4) and voice can change the rule without changing callers.
- **Runs.** A run is one agent execution with a state (`running`, `awaiting_confirmation`, `done`, `failed`), its messages, tool calls, gate decisions, `prompt_version` and token usage. A chat is a series of runs; scheduled runs later have no chat. Chats are private to the person who wrote them, kept until deleted.
- **System prompt.** Short English prompt files in the repository: role, rules, each offered plugin's guidance, the running skill's instructions, then a context block (date and time in the household time zone, household name, the person's name, role and language, the active plugins). Stable parts come first so providers can cache them.
- **Skills.** Declarative `SKILL.md` files contributed by plugins (ADR 0023): instructions, the allowed tools and the output (text or a JSON schema). A skill that reads untrusted text (for example pasted notes) gets no tools and returns typed output only, the reader rule of §8.1 in small.
- **Usage.** Every model request records the person, run, model and tokens; owners see totals per day, member and model. Field names follow the OpenTelemetry conventions for generative AI so §8.9's export can be added. Limits come later.
- **Evals.** Scripted models and a fake OpenAI-compatible server keep CI free and deterministic; real-model evals (Pydantic Evals) run on demand and report pass rates per dataset with the prompt and tool versions (ADR 0022).

### 8.1 Agents (Pydantic AI)

| Agent | Role | Sees untrusted content? | Tools |
|---|---|---|---|
| `reader` (quarantined) | Extract/classify docs, emails, tickets, web | Yes | **None**; typed Pydantic outputs only |
| `planner` (privileged) | Plans from trusted intent + typed reader outputs | No raw untrusted text | Read + proposal tools via gateway |
| `actor` | Executes approved plan steps | No | Write tools via gateway, one step at a time |
| `briefer` | Summaries | Typed data only | Read tools |
| `concierge` | Chat/voice front door | Own user's text | Delegates to planner |

This is a CaMeL-style split: control flow is separated from data flow so untrusted data cannot alter program flow (Debenedetti et al., "Defeating Prompt Injections by Design", arXiv:2503.18813 / IEEE SaTML 2026). Hauskraft uses **plan-then-execute + dual-LLM** by default and **action-selector** for kids/voice, drawn from Beurer-Kellner et al., "Design Patterns for Securing LLM Agents against Prompt Injections" (arXiv:2506.08837, 2025).

### 8.2 Tool access
Agents get only an MCP client pointed at the gateway, which lists tools filtered by `{agent, acting_user.role, data_class ceiling, time window}`. Pydantic AI's deferred tools / `ApprovalRequiredToolset` surface approval-required calls as `DeferredToolRequests`; workflows persist them and wait durably (DBOS `recv`). Arguments are validated *before* approval, so malformed calls never reach a human.

### 8.3 Policy model (Cedar)
Principal `User::<id>` or `Agent::<id>` acting for a user; action `Tool::"<plugin>.<tool>"` with annotations; resource = graph node/plugin; context `amount_eur`, `data_class`, `time`, `weekly_spend_eur`, `source_taint`, `channel`.

Defaults:
1. `read_only=false` → **deny** unless permitted.
2. `destructive=true` → **require_approval(owner)**.
3. `open_world=true` and `source_taint=untrusted` → **deny** (blocks injected exfiltration).
4. `money:propose` allowed up to weekly cap per category, above → approval; `money:execute` → deny (v1).
5. Kids/teens write only own chores/lists; quiet hours 21:00–07:00, no outbound messages.
6. External messages (tenant/contractor email) always need approval with diff preview.
7. Changing the deployment theme or installing a theme: `owner` only (from M1*, through the static role table of §2.3; any adult in M0*).

Effects: `allow`, `deny`, `require_approval{approvers, quorum, expires}`, `allow_with_limits{rate, amount}`. **Spend limits live in the gateway ledger, never the LLM**; LLM cost budgets are enforced in LiteLLM per virtual key. The M0* `authorize()` no-op hook in the service layer is the seam where this policy plugs in.

### 8.4 Approval inbox
Each request has a stable `approval_id`, human summary, before/after diff, data classes, triggering policy, expiry and trace. Channels: cockpit inbox (primary), HA actionable notification, optional Matrix/Signal/ntfy. Approver ≠ requester for `financial` above threshold; expired → auto-reject; approvals are audited; batch approval allowed for homogeneous low-risk items. Approve/Reject controls use fixed semantic tokens that every theme must render distinguishably (§10.2.5).

### 8.5 Data-class routing table (LiteLLM model groups)

| Data class | Default route | Cloud allowed? | Notes |
|---|---|---|---|
| public | cloud or local | Yes | |
| household | local preferred | Yes (owner toggle) | meals, chores, calendar titles |
| personal | local | Opt-in per plugin | contacts, gift notes |
| financial | local | Opt-in, with redaction (IBAN, names → tokens) | |
| tenant | **local only** | **No** | third-party personal data; cloud needs an Art. 28 DPA |
| child | **local only** | **No** | |
| health | **local only** | **No** | |
| secret | never sent to a model | No | |

The router fails closed: without a local model for a local-only class, the step uses a non-LLM path or asks the human.

### 8.6 Audit log
Append-only Postgres table: `seq, ts, actor, on_behalf_of, agent, tool, args_hash, args_redacted, policy_decision, approval_id, result_hash, verify_status, data_classes, trace_id, prev_hash, hash`, where `hash = SHA-256(prev_hash || canonical_json(row))`. A daily head-hash anchor is written to an HA sensor attribute and an external file/email. DB role forbids UPDATE/DELETE; retention per data class. M0*'s append-only `outbox_events` table is the feed this audit log will consume.

### 8.7 Failure handling and verification
Every write tool declares a `verify` read-back; the gateway sets `verify_status` to `ok|mismatch|unverifiable`, and the agent receives the verified status, not its own claim. User-facing summaries are generated from audit rows, not model narrative. Idempotency keys per plan step; DBOS step retries; per-plugin circuit breakers with health on the dashboard.

### 8.8 Prompt-injection defences (layered)
Reader/actor split; taint tracking (rule 3); per-agent tool allowlists; spotlighting untrusted text for the reader; no auto-follow of URLs (web fetch is a separate egress-allowlisted plugin); schema-only reader output, never concatenated into planner instructions; an AgentDojo-style red-team suite over household fixtures in CI.

### 8.9 Secrets and observability
SOPS+age for small installs, OpenBao/Vault optional; plugins get only declared secrets, injected at runtime, never logged; bank PINs never stored (FinTS PIN/TAN per session). OpenTelemetry traces core → gateway → plugin; LLM spans to self-hosted Langfuse or Arize Phoenix with prompt bodies redacted for classes ≥ `financial`; per-agent cost dashboards from LiteLLM spend logs.

## 9. Data model

### 9.1 Core entities (household graph)
`Person`, `Role`, `Contact` (vCard), `Place` (↔ HA areas), `Property`, `Unit`, `Asset`, `Document`, `Event` (iCal), `Task`, `Project`, `Transaction`, `Account`, `Contract`, `Lease`, `Tenancy` (Person×Unit×period), `RentExpectation`, `MeterPoint`, `MeterReading`, `CostItem` (BetrKV category, allocation key), `Statement`, `Ticket`, `Contractor`, `Deadline`, `Approval`, `Milestone`.

Typed edges: `owns`, `located_in`, `about`, `evidences`, `pays`, `party_to`, `assigned_to`, `due_for`, `measured_by`. Storage: Postgres tables per core type plus a generic `edge` table. JSON-LD export uses schema.org where it fits (Person, Place, Residence, Product, DigitalDocument, Event, Invoice, MonetaryAmount) and a `hauskraft:` vocabulary for the rest (Lease, CostAllocationKey, BetrKVCategory).

Configuration entities (not part of the graph): `DeploymentSetting` (key/value, e.g. `theme_id`, `household.name`, `household.timezone`, `household.locale`), `DashboardLayout` (per user), `PluginRecord`, `ThemeRecord` (discovered theme packages and validation results). Accounts (`User`, `Session`) live in core tables; from M1* a user also carries `must_change_password`.

### 9.2 System of record vs cache
- **External SoR:** store `external_ref {plugin, id, etag, synced_at}` plus a minimal projection for search/joins; scheduled pull + webhooks; writes go to the SoR via tools, then re-sync.
- **Cockpit SoR:** native tasks, rentals, deadlines, graph edges, PRM extras, milestones, approvals, audit, deployment settings, dashboard layouts.
- **Conflict rule:** SoR wins; projections are rebuildable (`hauskraft reindex <plugin>`).

### 9.3 Search/RAG
Hybrid Postgres full-text + pgvector (sqlite-vec on the add-on tier) with local embeddings on M/L tiers. Chunks inherit data class; retrieval filters by the requester's role **before** ranking; `child/health/tenant` embeddings are generated locally only.

### 9.4 Backup/export
`hauskraft backup` dumps Postgres + object store + config + installed theme packages (age-encrypted) and lists external tools needing their own backups. Exports: JSON-LD, ICS, vCard, CSV (rent ledger), PDF (statements), and a one-click per-tenant GDPR Art. 15 export.

## 10. Dashboard and UI specification

### 10.1 Information architecture
*Today* (default), *Inbox* (approvals, documents to classify, extractions to confirm; M1+), domain pages (Home & Assets, Rentals, Money, Family, Food, Projects, Documents, Vehicles), *Activity*, global *Search*/command palette, *Settings* (in this order: Appearance, Account, Household, Members, Assistant, later Plugins; Household, Members and Assistant only for owners, §2.3, §8.0). The *Assistant* side panel opens from a fixed shell button on every page once an owner has set up the assistant; it is part of the shell, so every theme renders it with the same functions. One navigation model (`NavModel`) defines the items, their order, labels and icons; every navigation style renders that same model.

### 10.2 Theming system

#### 10.2.1 What a theme may change

| Level | A theme may change | Notes |
|---|---|---|
| **A. Tokens** | Colours (semantic roles), typography (families, scale, weights, line heights), shape (radius scale), spacing scale, elevation (shadows), motion durations, focus ring, app background (colour, gradient or bundled image) | Light and dark token sets are both required |
| **B. Component styles** | Widget chrome (`flat` · `outlined` · `elevated` · `tinted`), widget header (`inline` · `banner`), primary button style (`solid` · `soft` · `outline`), checkbox style (`square` · `round`), icon pack, empty-state illustrations | Fixed enums; the shell maps them to `@hauskraft/ui` variants |
| **C. Layout (limited)** | Navigation style on wide screens (`sidebar` · `topbar`), on narrow screens (`bottom-tabs` · `drawer`); density (`compact` · `comfortable` · `spacious`); content width (`full` · `contained`) | Grid stays 12 columns so saved layouts remain valid; density changes spacing, control size, grid row height and gutters only |
| **D. Custom CSS or scripts** | **Not allowed** | Revisit later; would need sandboxing and review |

#### 10.2.2 Function invariance (normative)
A theme can never add, remove, reorder, rename, relabel or hide functions. Across all themes the cockpit has the same routes, navigation items and order, widgets, controls, labels (i18n strings cannot be overridden by themes), keyboard shortcuts, accessible names and focus order.

Enforcement:
1. **Themes are data, not code.** The shell interprets a fixed schema; there is no hook for theme logic.
2. **One navigation model.** All navigation renderers consume the same `NavModel`.
3. **ARIA snapshot tests.** CI renders every view in every built-in theme (light and dark, wide and narrow viewport) and compares the accessibility tree of the `main` landmark exactly (only the theme picker's own selected state is masked) and the navigation item list (names and order, with drawers expanded) across themes. Any difference fails the build.
4. **Readability is function.** A control nobody can read is effectively hidden, so required contrast pairs are hard requirements (§10.2.5): a theme that fails them is rejected, not just warned about.

#### 10.2.3 Scope of a theme
- **One active theme per deployment.** Everyone sees the same theme on every device. Stored in `deployment_settings.theme_id`; the default comes from `HAUSKRAFT_DEFAULT_THEME` (falls back to the built-in default theme).
- **Who switches it:** any adult in M0*; `owner` only once RBAC lands (policy rule 7, §8.3).
- **Colour mode is per device.** Each device chooses `system` (default), `light` or `dark`, stored in that browser. A wall tablet can go dark at night while a phone stays light; both use the same theme.
- **Later (not v0.2):** per-user or per-device theme overrides, with precedence device > user > deployment.

#### 10.2.4 Theme package format
A theme is a plugin of type `theme` (§5.3). It contains no code.

```text
hackspace/
  hauskraft.plugin.json        # type ["theme"], runtime.kind "declarative"
  theme.json                  # Hauskraft theme definition (schema below)
  tokens.light.json           # DTCG 2025.10 design tokens, light mode
  tokens.dark.json            # DTCG 2025.10 design tokens, dark mode
  assets/fonts/*.woff2        # self-hosted fonts only
  assets/images/*             # backgrounds, empty states (png, webp, avif, svg)
  assets/icons/sprite.svg     # optional icon pack (symbols keyed by semantic icon name)
  LICENSE  LICENSES/          # theme licence + font/icon licences
```

Token files use the Design Tokens Community Group format, whose first stable version (2025.10) was published in October 2025, so themes can come out of Figma, Tokens Studio or Penpot pipelines. Hauskraft defines which semantic token names must exist (§10.2.5). Light and dark are two files so the loader does not depend on any optional DTCG module.

`hauskraft.plugin.json`:

```json
{
  "$schema": "https://hauskraft.dev/schema/plugin/1.0.json",
  "id": "dev.hauskraft.theme.hackspace",
  "name": "Hackspace",
  "version": "0.1.0",
  "type": ["theme"],
  "hauskraft_api": "^0.1.0",
  "license": "MIT",
  "authors": [{ "name": "Hauskraft contributors" }],
  "source": "https://github.com/hzmchen/hauskraft/tree/main/themes/builtin/hackspace",
  "runtime": { "kind": "declarative" },
  "capabilities": [],
  "data_classes": { "reads": [], "writes": [], "emits": [] },
  "contributes": { "themes": [{ "id": "hackspace", "file": "theme.json" }] }
}
```

`theme.json`:

```json
{
  "$schema": "https://hauskraft.dev/schema/theme/1.0.json",
  "theme_api": "1.0",
  "name": "Hackspace",
  "description": "Basement hackerspace look: near-black, phosphor green, monospace, pixel icons. Dark is its home turf.",
  "tokens": { "light": "tokens.light.json", "dark": "tokens.dark.json" },
  "fonts": [
    { "family": "JetBrains Mono", "src": "assets/fonts/JetBrainsMono-Variable.woff2", "weight": "100 800", "style": "normal" },
    { "family": "VT323", "src": "assets/fonts/VT323-Regular.woff2", "weight": "400", "style": "normal" }
  ],
  "components": {
    "widget": { "chrome": "tinted", "header": "banner" },
    "button": { "primary": "solid" },
    "checkbox": { "style": "square" }
  },
  "layout": {
    "navigation": { "wide": "topbar", "narrow": "bottom-tabs" },
    "density": "compact",
    "content_width": "contained"
  },
  "icons": { "pack": "assets/icons/sprite.svg", "fallback": "default" },
  "background": { "light": { "color": "{color.background}" }, "dark": { "image": "assets/images/grid-dark.webp" } },
  "preview": { "swatches": ["{color.primary}", "{color.accent}", "{color.background}"] }
}
```

(`name` is a plain string; theme names are proper nouns and are not translated.)

#### 10.2.5 Semantic token contract (theme API 1.0)

| Group | Required tokens |
|---|---|
| Colour, surfaces | `color.background`, `color.foreground`, `color.surface`, `color.surface-foreground`, `color.muted`, `color.muted-foreground`, `color.border`, `color.input`, `color.ring`, `color.overlay` |
| Colour, roles | `color.primary`, `color.primary-foreground`, `color.secondary`, `color.secondary-foreground`, `color.accent`, `color.accent-foreground`, `color.destructive`, `color.destructive-foreground`, `color.success`, `color.success-foreground`, `color.warning`, `color.warning-foreground`, `color.info`, `color.info-foreground` |
| Colour, chrome | `color.nav-background`, `color.nav-foreground`, `color.nav-active`, `color.nav-active-foreground`, `color.widget-background`, `color.widget-foreground`, `color.widget-border` |
| Colour, data | `color.chart-1` … `color.chart-6` |
| Typography | `font.sans`, `font.heading`, `font.mono`, `font-size.xs` … `font-size.3xl`, `font-weight.regular`, `font-weight.medium`, `font-weight.bold`, `line-height.tight`, `line-height.normal` |
| Shape | `radius.sm`, `radius.md`, `radius.lg`, `radius.xl`, `radius.full` |
| Spacing | `space.unit` (density multiplies it) |
| Elevation | `shadow.sm`, `shadow.md`, `shadow.lg` |
| Motion | `duration.fast`, `duration.normal`, `easing.standard` (always reduced to 0 under `prefers-reduced-motion`) |

Compilation: tokens become CSS custom properties `--hauskraft-<group>-<name>` and are aliased to the variable names shadcn/ui expects (`--background`, `--primary`, `--radius`, …), so `@hauskraft/ui` components work unmodified. Tailwind v4 `@theme inline` maps utility classes (`bg-primary`, `text-muted-foreground`, `rounded-lg`) onto these variables.

**Hard requirements (theme rejected if violated), checked in both modes:**
- Text contrast ≥ 4.5:1 (WCAG 2.2 AA) for: foreground/background, surface-foreground/surface, muted-foreground/background, primary-foreground/primary, secondary-foreground/secondary, accent-foreground/accent, destructive-foreground/destructive, success/warning/info foreground pairs, nav-foreground/nav-background, nav-active-foreground/nav-active, widget-foreground/widget-background.
- Non-text contrast ≥ 3:1 for `color.border`, `color.input` and `color.ring` against background and surface.
- `color.destructive` and `color.primary` must be clearly distinguishable (minimum OKLCH distance; value fixed in ADR-0013) so "Delete" never looks like "Save".
- All required tokens present; values parse as valid CSS colours, lengths, durations or font stacks; aliases resolve without cycles.

#### 10.2.6 Icons
Icons are referenced by semantic name, never by file: `nav.today`, `nav.tasks`, `nav.activity`, `nav.settings`, `action.add`, `action.edit`, `action.delete`, `action.confirm`, `action.cancel`, `status.done`, `status.due`, `status.overdue`, `user.menu`, `mode.system`, `mode.light`, `mode.dark`, `widget.unavailable` (core set v1). Plugins introduce new names through `contributes.icons[]` with a default SVG. A theme may supply a sprite with any subset; missing names fall back to the default pack (Lucide). Icons keep their accessible labels from the component, never from the theme.

#### 10.2.7 Distribution and installation
- **Built-in themes** ship in the image under `themes/builtin/`. M0* ships three: `default` (neutral, sidebar/drawer, comfortable, outlined cards, Lucide), `paper` (high contrast, flat cards, top bar/drawer, compact, serif headings) and `hackspace` (underground hackerspace style: near-black with phosphor green and magenta, monospace type, square corners, tinted panels with title bars, top bar/bottom tabs, compact, pixel icon pack). Hackspace is inspired by the Berlin hacker scene but uses no name, logo or artwork of any real club or event.
- **Third-party themes** are folders dropped into the themes volume (`HAUSKRAFT_THEME_PATHS`, default `/data/themes`), discovered at API start (hot reload later) and listed in Settings → Appearance with their validation result. Invalid themes are listed with reasons but cannot be selected.
- **No in-app editor.** Authors use a template folder, the authoring guide and `hauskraft themes validate <path>`.
- **Registry and signing** follow the plugin registry once it exists (M5+).

#### 10.2.8 Runtime behaviour
- The API compiles the active theme to one stylesheet, `GET /api/v1/theme/active.css` (strong ETag = hash of theme content), and serves its assets from `/api/v1/theme/assets/{theme_id}/{path}`. Light tokens go on `:root`, dark tokens on `:root.dark`.
- `index.html` links the stylesheet directly, and a small inline head script sets `.dark` from the device's mode before first paint (no flash). A bundled copy of the default theme is the fallback if the stylesheet fails to load.
- Clients refetch theme metadata every 60 seconds and on window focus; when the hash changes they swap the stylesheet without a reload. (Live push over the event bus later.)
- Changing the deployment theme is a normal governed write: service layer, `authorize()`, outbox event `hauskraft.settings.theme_changed`.

#### 10.2.9 Rules for widget and page authors (normative)
- Use only `@hauskraft/ui` primitives and semantic utility classes. No colour literals (hex, rgb, hsl, oklch), no Tailwind default palette classes (`bg-red-500`), no arbitrary values (`p-[13px]`), no inline styles for colour, font or spacing. Lint rule `hauskraft/no-raw-styles` enforces this in `apps/web` and `plugins/**/web`.
- Icons only through `<Icon name="…">`.
- Respect density through spacing utilities and `@hauskraft/ui` sizes; never hard-code row heights.
- **Iframe widgets (MCP Apps):** the host passes the active theme to each view through MCP Apps host context: the light/dark mode plus a set of CSS variables (`McpUiHostContext.styles.variables`), which the official ext-apps SDK applies to the view. The cockpit maps its semantic tokens onto those variable names. Views that ignore host variables will look off-theme; registry review flags them.

### 10.3 Widget system
react-grid-layout grid per role or user, 12 columns, layouts stored as JSON. Widgets are first-party React components (bundled at build time from plugin web packages) or, from M5, **MCP Apps** views (`ui://` resources in sandboxed iframes, postMessage JSON-RPC). The host enforces CSP from resource metadata and routes widget tool calls through the gateway with the *viewing user's* permissions. Each widget sits in an error boundary; unknown widgets render a "Widget unavailable" card.

### 10.4 Generative UI
Agents return either a `ui://` reference from an installed plugin or a constrained declarative card (list, table, chart, form, approval) rendered by the host with `@hauskraft/ui`, so it follows the active theme. Never arbitrary HTML. A2UI-style specs are a watch item.

### 10.5 Kiosk/wall mode (M5)
`kiosk` role with device-bound token; large type, auto-rotating pages, presence-aware via HA, night dimming (uses the device colour mode); no approvals except kid chore ticks.

### 10.6 Mobile PWA (M5)
Offline Today and shopping list, Web Push and/or HA app notifications, share-target to send photos/PDFs to Paperless.

### 10.7 Role views
Icon-first chore boards for kids; own schedule for teens; a single "care sheet" for caregivers; a minimal separate tenant portal (tickets, documents, meter-reading form, statements). All role views use the deployment theme.

## 11. Security and privacy

### 11.1 STRIDE threat model (abridged)

| Threat | Vector | Mitigation |
|---|---|---|
| **S**poofing | Stolen HA token; forged approval via notification | Non-admin HA user; approvals bound to cockpit identity; step-up PIN; short-lived OAuth |
| **S**poofing (UI) | A theme makes "Approve" look like "Reject", or "Delete" like "Save" | Fixed variant semantics; destructive/primary distinguishability rule; contrast rules; ARIA invariance tests |
| **T**ampering | Malicious plugin update; audit edits | Signed artifacts + digest pinning; capability diff on upgrade; hash-chained audit with anchor |
| **T**ampering (theme) | CSS injection through token values; SVG with script | No raw CSS accepted; every value type-checked and serialised by the compiler; SVG sanitised to an element/attribute allowlist; strict CSP (`default-src 'self'`, no inline script except the hashed mode script) |
| **R**epudiation | "I didn't approve that" | Immutable audit with approver, channel, device |
| **I**nfo disclosure | Cloud LLM sees child/tenant data; exposed Ollama; plugin exfiltration | Fail-closed router; internal-only LLM endpoints; per-plugin egress allowlists; taint rule |
| **I**nfo disclosure (theme) | Remote fonts or images as tracking beacons | Themes may reference only their own bundled assets; no external URLs anywhere; fonts self-hosted |
| **D**oS | Runaway agent loops; LLM spend; oversized theme assets | Iteration caps; LiteLLM budgets; circuit breakers; theme limits (10 MB total, 2 MB per asset, max 8 font files) |
| **E**levation | Prompt injection → writes; marketplace skill with shell (ClawHub); OpenClaw-style token-leak RCE (CVE-2026-25253) | Reader/actor split; no shell/exec capability exists; container isolation; no auto-connect to arbitrary gateway URLs; origin checks on WS; themes carry no code |

### 11.2 GDPR / DSGVO
- **Household data:** purely personal/family processing falls under Art. 2(2)(c) GDPR, which courts interpret narrowly; publishing to the internet breaks it.
- **Tenant data is NOT covered.** AG Wiesbaden (Teilurteil of 26.04.2021, Az. 93 C 2338/20), upheld by LG Wiesbaden (Urteil of 30.09.2021, Az. 3 S 50/21), held that a private landlord owed a tenant an Art. 15 access response and rejected the household exemption.
- **Mandatory `rentals` features:** records-of-processing template, tenant privacy notice template, retention schedule, Art. 15 export, local-only LLM processing, no cloud LLM without an Art. 28 DPA. An exposed tenant portal implies TLS, rate limiting, separate auth realm and minimal data.
- **Children's data** is local-only; caregiver access is time-boxed and logged.
- **Themes** never see household data: they are static and applied client-side.
- This spec provides tooling, not compliance guarantees, and is not legal advice.

### 11.3 Network exposure
LAN-only by default; remote access via WireGuard/Tailscale (HA Cloud for HA). If the tenant portal is enabled, only `/portal` is exposed via the reverse proxy; cockpit and gateway are never internet-facing. The M0* demo runs over plain HTTP on localhost with `Secure` cookies off; any LAN exposure requires TLS.

## 12. Gap analysis: reuse vs build

**Reuse:** Mealie, Grocy, Donetick, Vikunja/Plane, Paperless-ngx, Actual/Firefly, Wallos, LubeLogger, Homebox, Baby Buddy, Radicale, HA (energy, todo, calendar, notify, Assist, MCP Server), LiteLLM, Ollama/llama.cpp, Langfuse, n8n (optional), shadcn/ui, Tailwind, DTCG token tooling (Figma/Tokens Studio/Penpot export).

**Build (ranked by value):**
1. **`tool-gateway` household policy profile:** Cedar, approvals, spend ledger, verify hooks, hash-chained audit.
2. **Approval inbox + HA actionable approval bridge.**
3. **`rentals` plugin (DACH-first):** leases, tenancies, rent expectations and reconciliation; BetrKV categories, allocation keys, HeizkostenV consumption split hand-off, CO2KostAufG split; statement PDF; §556 BGB deadlines; §6a HeizkostenV consumption-information reminders; tickets, contractors, tenant portal.
4. **`deadlines` engine** with extraction-with-provenance from Paperless.
5. **Household graph + data-class-aware hybrid search.**
6. **Cockpit web app** with widget grid and MCP Apps host.
7. **Theming system:** theme schema, validator and compiler, `@hauskraft/ui` themed primitives, navigation renderers, function-invariance test suite, built-in themes and authoring kit. No existing self-hosted dashboard offers swappable, validated, data-only themes with guaranteed function invariance.
8. **`hauskraft` HA custom integration.**
9. **FinTS bridge plugin** (read-only, user-registered ID) and bank-provider abstraction (Enable Banking / FinTS / CSV-CAMT).
10. **Kids milestones/school/activities module** (local-only).
11. **Minimal health log**, since Fasten OnPrem is archived.

## 13. Roadmap, repository structure, contribution model

### 13.1 Milestones

- **M0\* Scaffolding MVP** (replaces M0). Monorepo, CI, Compose; core-api with local session auth (OIDC seam) and the role enum (only `adult` enabled); migrations; in-process plugin loader; native `tasks` plugin (shared list: title, done, optional due date; any adult may edit or delete any task); web shell with Today grid, All tasks page and Activity feed; CloudEvents outbox; `authorize()` no-op seam; theming system with three built-in themes, deployment-wide theme and per-device colour mode; en/de. **No** third-party integrations (HA counts as one; `NullBridge` only), gateway, agents, approvals, registry or signing. *AC:* the demo script in `docs/backlog/m0-star/README.md` (12 steps, automated in Playwright) and green CI. Detailed in 13 epics / 61 stories. **Done 2026-10-22.**
- **M1\* Household basics** (C8). A real household installs Hauskraft without demo data, sets it up in the browser, brings in its members and runs its own accounts: first-run wizard; `owner` and `adult` roles through a static permission table behind `authorize()`; My account (profile, password, sessions); member management for owners; household settings (name, time zone, default language); sign-in polish; a settings area; account events in Activity (§2.3). **No** policy engine, approvals, gateway, MCP or agent skills, LLM routing, HA, OIDC, teen/kid roles, email, backup or release images. *AC:* the demo script in `docs/backlog/m1-star/README.md` (automated in Playwright), the M0* demo still passing, and green CI.
- **M2\* Agentic harness** (C13). Members chat with an assistant in a side panel that runs plugin tools on their behalf; skills turn pasted text into tasks and write a weekly overview; owners connect an OpenAI-compatible endpoint and see token usage; evals measure the harness. One tool contract and registry (§5.3, ADR 0019), a gate with confirmation for destructive tools, encrypted endpoint key, usage records. **No** schedules, approval inbox, risk classifier, budget limits, MCP server or client, streaming, voice, data-class routing or Cedar; each is listed with its seam in the backlog. *AC:* the demo script in `docs/backlog/m2-star/README.md` (automated in Playwright against a fake model), the M0\* and M1\* demos still passing, green CI, and one documented eval run against a real endpoint.
- **Capability ladder (after M2\*).** The milestones below remain the direction. Their order and cut are re-planned one milestone at a time from the project backlog.
- **M1 Governed gateway + HA bridge (3–5 wks):** MCP aggregation, Cedar behind `authorize()`, audit chain fed from the outbox, LiteLLM class routing, verify hooks; ha-bridge v0 replacing `NullBridge`; OIDC `IdentityProvider`; RBAC for owner/adult/teen/kid. *AC:* unpermitted write denied; approval calls appear in the inbox; tampering any audit row fails `hauskraft audit verify`; a `child` prompt with no local model fails closed; HA entity widget live.
- **M2 MVP domains (4–6 wks):** Vikunja, Donetick, Paperless, Actual, Mealie, Grocy, CalDAV connectors; weekly briefing; HA integration v0. *AC:* Journey 1 runs end-to-end on a fixture household; approval via HA notification works; every item links to its source.
- **M3 Deadlines + documents (3–4 wks):** reader extraction with provenance; contract deadlines; Wallos; HA calendar/todo publication. *AC:* ≥90% of notice dates correct across 20 fixture contracts after the confirmation UI; zero deadlines scheduled without confirmation.
- **M4 Rentals v1 (6–8 wks):** leases, reconciliation (Enable Banking + CSV/CAMT), Nebenkosten calculation + PDF, §556 countdown, tickets, contractors, GDPR toolkit. *AC:* golden-file tests vs hand-calculated statements; 100% deterministic reconciliation on fixtures; complete Art. 15 export.
- **M5 v1.0 (4–6 wks):** SDK + registry + signing (plugins and themes); runtime plugin install; MCP Apps host (with theme variables); kiosk; PWA; tenant portal; FinTS; kids module; red-team suite; decision on per-user/per-device theme overrides. *AC:* an SDK-only third-party plugin and a third-party theme install from the registry; unsigned artifacts refused; zero successful injected writes.
- **M6+ Ecosystem:** Firefly, Plane, Homebox, LubeLogger, Baby Buddy, Ghostfolio, Monica connectors; n8n bridge; Temporal option; HA-theme importer; more translations.

### 13.2 Repository structure

```
hauskraft/
  apps/web/                 # React+Vite shell (AGPL)
  services/core_api/        # FastAPI, RBAC, graph API, approvals, theme registry (AGPL)
  services/gateway/         # MCP gateway, Cedar, audit, verify (AGPL, M1)
  services/agents/          # Pydantic AI agents, evals (AGPL, M1+)
  services/workflows/       # DBOS workflows (AGPL, M2+)
  services/plugin_host/     # manifest verify, supervisor, egress cfg (AGPL, M5)
  packages/sdk-py/ sdk-ts/  # SDKs (MIT)
  packages/ui/              # @hauskraft/ui themed primitives (MIT)
  packages/schemas/         # JSON Schemas: manifest, theme, events, graph, policies (MIT)
  plugins/official/*        # connectors & domain plugins (MIT)
  themes/builtin/*          # default, paper, hackspace (MIT + OFL fonts)
  themes/template/          # starting point for theme authors (MIT)
  integrations/ha-hauskraft/ # HA custom integration (MIT, M1+)
  deploy/compose/ deploy/ha-addon/
  docs/spec/ docs/adr/ docs/backlog/ docs/testing/ docs/themes.md
  tests/                    # spec-owned acceptance suite + fixtures (MIT), written before the code
  fixtures/household/       # synthetic family, properties, bank CSVs
  AGENTS.md  LICENSING.md
```

**AGENTS.md rules (summary):** every PR references a spec section or story, includes contract tests and updates JSON Schemas first; no new capability strings or theme tokens without an ADR; no network calls in unit tests; never weaken a default-deny policy in fixtures; no raw styles in UI code.

### 13.3 Quality: test-driven development
Every story is built red → green → refactor (ADR-0014).
- **Spec-owned acceptance suite.** `tests/` is written from this spec and the backlog before the code: static contract tests (schemas, fixtures, config), black-box CLI tests, live HTTP tests against the running stack, and Playwright tests of the demo script, the tasks UI and theme invariance. Fixtures (valid and invalid manifests, events, theme packages) are part of the contract.
- **One switch per story.** `tests/story-status.json` marks each story red or green. Red stories' tests run as expected failures; green stories' tests are hard gates; CI fails when a red story's tests all pass, so the switch cannot be forgotten.
- **Black box first.** Tests talk to public surfaces only (HTTP API, CLI `--json`, linters via stdin, roles and accessible names in the UI), so implementers keep freedom inside modules. Unit and integration tests are written first inside each story.
- **CI time budget.** Every CI job aims to finish in under 8 minutes and has a hard limit of 8, except `unit-web` with
  15 (D15). Its browser install fetches about 26 MB of system packages from the runner's apt mirror, which at times
  serves ~40 KB/s, and that alone overran 8 minutes while the tests take ~20 seconds. The limit stops runaway jobs;
  it should not fail a PR because of a slow mirror. Running the job in the Playwright container image or caching the
  packages would bring it back to 8 (NIE-87).
- **Agent behaviour is measured, not assumed (M2\*).** Scripted models and a fake OpenAI-compatible server test the harness deterministically in every CI run. Real-model evals run on demand: datasets per use case, repeated cases, pass-rate thresholds (100% for safety cases) and a report naming the model, prompt version and tool versions (ADR 0022).
- **Docs are tested too.** `scripts/backlog_tools.py check` and `tests/meta/` keep the spec, backlog, story status and test coverage consistent.

### 13.4 Contribution model
DCO sign-off; ADRs for architecture changes; plugin quality tiers mirroring HA's scale (bronze: manifest + config flow + tests; silver: verify hooks + diagnostics; gold: themed widgets + i18n + docs); theme quality tier "verified": valid schema, AA contrast in both modes, passes invariance suite, licences for every font and icon; private security disclosure; review rota for `verified` plugins and themes; BDFL → small steering group at 1.0.

## 14. Open questions and risks

1. **Name clash (resolved).** Hearth (hearthdisplay.com) is a commercial family organiser in the same space: a wall-mounted touchscreen with shared calendars, chores, lists, meal planning and an AI helper. The working name HearthOS was replaced by Hauskraft before the public release (D10, ADR 0015). Several small unrelated open-source projects are also called Hearth.
2. **Upstream fragility:** Grocy single-maintainer, Monica's rebuild, Fasten archived. Mitigation: SoR-agnostic graph, export-first, alternatives per domain.
3. **Bank access in DE:** Enable Banking in Actual was experimental as of 26.6.0 and PSD2 consent caps sync at 90 days. FinTS needs per-user registration and TAN interaction. Design for CSV/CAMT fallback.
4. **Nebenkosten correctness:** HeizkostenV/CO2KostAufG rules and case law change. Ship as draft-for-review with versioned rule packs, golden tests and DACH landlord/tax-adviser reviewers.
5. **GDPR for landlords:** a tenant portal raises obligations; keep it optional and email-based for small landlords.
6. **MCP spec churn:** pin SDKs and run conformance tests per release; MCP Apps host-variable names may evolve, so the token mapping lives in one versioned file.
7. **HA API deprecations:** the LLM tool API changed in 2026.10; run CI against HA beta.
8. **Local model quality:** read-back verification and confirmation UIs are mandatory.
9. **Licensing of closed in-process plugins** is unsettled: keep the SDK minimal and MIT; prefer out-of-process for closed plugins.
10. **Theme expressiveness vs safety:** without custom CSS, some designs are impossible. Watch demand; any future custom-CSS tier needs sandboxing, a review tier and invariance tests.
11. **Per-user/per-device themes** are deferred; the data model (`deployment_settings`) should not block adding `user_preferences.theme_id` later.
12. **Scope creep:** hold the line on M0*, then the household basics (M1*), then the agentic harness (M2*), then gateway and HA, then M2 domains, rentals and governance.
16. **Confirmation fatigue.** Asking before every destructive call trains people to click yes. M2\* logs every gate decision so confirmation rates can be measured; a risk classifier (like an "auto mode") and the approval inbox build on the same gate (ADR 0020).
17. **Model quality varies.** Tool calling on small or local models is unreliable, and every tool costs tokens on every request. Keep tool sets small per run, tools coarse and outputs compact (token budgets are tested), and check a model with the evals before relying on it.
13. **Unverified items:** A2UI-style declarative UI standards; long-term stability of OpenProperty forks.
14. **How plugins reach agents (decided, ADR 0019).** One tool contract and an in-core registry; skills on top; MCP as an adapter at the edges (exposing the registry to outside agents, wrapping outside MCP servers as tools). The gateway of §8.2 builds on the registry.
15. **First visitor wins at setup.** Between `docker compose up` and finishing the wizard, anyone who can reach the port can claim the install (ADR 0017). The docs tell operators to finish setup right after starting the stack and to keep it on localhost or a trusted LAN until then.

## Appendix: decision log (since v0.1)

| ID | Decision | Date |
|---|---|---|
| D1 | CloudEvents extension attributes `dataclass` and `actorid` (no underscores) | 2026-10-12 |
| D2 | Core AGPL-3.0-or-later; SDKs, schemas, UI kit, official plugins, built-in themes and HA integration MIT; fonts OFL-1.1 | 2026-10-12 |
| D3 | M0* shared task list: any adult may edit or delete any task | 2026-10-12 |
| D4 | Theming: levels A + B + limited C (navigation style, density, content width); no custom CSS; themes as packages only, no editor; built-in themes; one theme per deployment; colour mode per device | 2026-10-12 |
| D5 | Themes never move, hide, rename or reorder functions | 2026-10-12 |
| D6 | HearthOS stays the working name; rename before public release. Superseded by D10 (ADR 0015) | 2026-10-12 |
| D7 | Home Assistant counts as a third-party integration for M0*; only a `NullBridge` stub | 2026-10-12 |
| D8 | Built-in themes: Default, Paper and Hackspace (underground hackerspace style, no third-party names or logos) | 2026-10-12 |
| D9 | Red/green TDD with a spec-owned acceptance suite and per-story status switch (ADR-0014) | 2026-10-12 |
| D10 | Renamed from HearthOS to Hauskraft before going public: code namespace `hauskraft`, plugin and theme IDs `dev.hauskraft.*`, schema and problem URLs on hauskraft.dev (ADR 0015) | 2026-10-21 |
| D11 | The milestone after M0* is M1* Household basics; capability work (gateway, MCP or agent skills, Cedar, approvals, LLM routing, HA, OIDC) is deferred and re-planned afterwards | 2026-10-22 |
| D12 | M1* enables `owner` and `adult` through a static permission table behind `authorize()`; Cedar later (ADR 0016) | 2026-10-22 |
| D13 | First-run setup is a web wizard; the first visitor becomes owner, with no setup code (ADR 0017) | 2026-10-22 |
| D14 | Changes to members and passwords are CloudEvents shown in Activity (ADR 0018) | 2026-10-22 |
| D15 | CI job `unit-web` may run 15 minutes instead of 8, because its browser install depends on a slow apt mirror (§13.3); the 8-minute target stays | 2026-10-23 |
| D16 | The milestone after M1\* is M2\* Agentic harness; schedules, the approval inbox, a risk classifier, budget limits, MCP, streaming, voice and data-class routing come later, and the design must not block them | 2026-10-24 |
| D17 | Plugins expose tools through one contract and an in-core registry; skills sit on top; MCP is an adapter at the edges (ADR 0019) | 2026-10-24 |
| D18 | The assistant acts with the person's permissions; events carry `agentrunid`; a swappable gate decides allow, confirm or deny, with confirmation for destructive tools in M2\* (ADR 0020) | 2026-10-24 |
| D19 | The owner sets an OpenAI-compatible Chat Completions endpoint in the web UI; the key is AES-GCM-encrypted in the database (ADR 0021) | 2026-10-24 |
| D20 | Owners and adults may use the assistant; tools are on by default and owners can switch them off; chats are private and kept until deleted | 2026-10-24 |
| D21 | Evals in two layers: scripted and fake-model tests in every CI run, real-model evals on demand (ADR 0022); skills are `SKILL.md` bundles (ADR 0023) | 2026-10-24 |

## Sources (selected)
- Design Tokens Format Module 2025.10 (first stable version): https://www.designtokens.org/ and https://www.w3.org/community/design-tokens/2025/10/28/design-tokens-specification-reaches-first-stable-version/
- MCP Apps specification (SEP-1865): https://modelcontextprotocol.io/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp and https://github.com/modelcontextprotocol/ext-apps
- CloudEvents 1.0.2 naming conventions: https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md
- Home Assistant MCP Server: https://www.home-assistant.io/integrations/mcp_server/ ; LLM API: https://developers.home-assistant.io/docs/core/llm/
- Pydantic AI deferred tools and DBOS: https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/ , https://ai.pydantic.dev/durable_execution/dbos/
- Vikunja v2.7.0 (built-in MCP): https://github.com/go-vikunja/vikunja/releases/tag/v2.7.0
- Knuspr MCP docs: https://www.knuspr.de/en-DE/mcp-docs ; Picnic HA integration: https://www.home-assistant.io/integrations/picnic/
- CaMeL: https://www.computer.org/csdl/proceedings-article/satml/2026/785900a587/2jZks3ksGT6
- Landlord GDPR (LG Wiesbaden): https://www.datenschutzticker.de/2021/11/auch-bei-einem-privater-vermieter-kann-der-anwendungsbereich-der-dsgvo-eroeffnet-sein/
- Hearth Display (name clash): https://hearthdisplay.com/
- Full source lists: research reports of 2026-10-12 (landscape and spec v0.1).
