<!-- SPDX-License-Identifier: MIT -->
# Architecture decision records

Hauskraft records architecture decisions as [MADR 4](https://adr.github.io/madr/) files in this folder (ADR-0001). An ADR is required before changing a seam (`authorize()`, the plugin loader, the outbox, `IdentityProvider`), a schema in `packages/schemas`, or the theme contract.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-stack-split.md) | Stack split: Python backend, TypeScript frontend | Accepted |
| [0003](0003-licence-split.md) | Licence split: AGPL core, MIT plugin-facing parts | Accepted |
| [0004](0004-in-process-plugin-loader.md) | In-process plugin loader for M0* | Accepted |
| [0005](0005-auth-for-m0.md) | Auth for M0*: local accounts and server-side sessions | Accepted |
| [0006](0006-service-layer-authorize-seam.md) | Service layer and `authorize()` seam | Accepted |
| [0007](0007-cloudevents-transactional-outbox.md) | CloudEvents and a transactional outbox | Accepted |
| [0008](0008-data-classes-as-tags.md) | Data classes as tags | Accepted |
| [0009](0009-uuidv7-ids.md) | UUIDv7 IDs generated in the app | Accepted |
| [0010](0010-client-generation.md) | API client generation with hey-api | Accepted |
| [0011](0011-typescript-6-0.md) | TypeScript 6.0 for M0* | Accepted |
| [0012](0012-widget-grid.md) | Widget grid: react-grid-layout v2 | Accepted |
| [0013](0013-theming.md) | Theming: data-only theme packages and validator thresholds | Accepted |
| [0014](0014-tdd-spec-owned-acceptance-tests.md) | Test-driven development with spec-owned acceptance tests | Accepted |
| [0015](0015-rename-to-hauskraft.md) | Rename HearthOS to Hauskraft | Accepted |
| [0016](0016-static-role-permissions.md) | Static role permission table behind `authorize()` for M1* | Accepted |
| [0017](0017-first-run-setup.md) | First-run setup in the browser: the first visitor becomes owner | Accepted |
| [0018](0018-account-events.md) | Account changes are CloudEvents | Accepted |
| [0019](0019-tool-contract-and-registry.md) | One tool contract and an in-core registry; MCP at the edges | Accepted |
| [0020](0020-assistant-acts-on-behalf.md) | The assistant acts on behalf of a person, through a swappable gate | Accepted |
| [0021](0021-assistant-endpoint-and-key.md) | Owner-configured Chat Completions endpoint with the key encrypted at rest | Accepted |
| [0022](0022-evals-in-two-layers.md) | Evals in two layers: free scripted tests in CI, real-model evals on demand | Accepted |
| [0023](0023-skill-format.md) | Skills are `SKILL.md` bundles contributed by plugins | Accepted |

## Writing a new ADR

1. Copy the template below to `NNNN-kebab-title.md` with the next free number.
2. Open it with status `Proposed` in the same PR as the change it justifies; the reviewer sets `Accepted`.
3. Add a row to the table above. Never rewrite an accepted ADR; supersede it with a new one and set the old one to `Superseded by ADR-NNNN`.

```markdown
---
status: Proposed
date: YYYY-MM-DD
---

# Title in the imperative or as the chosen option

## Context and problem statement

What forces are at play? Which question does this ADR answer?

## Decision drivers

* …

## Considered options

* Option A
* Option B

## Decision outcome

Chosen option: "…", because …

### Consequences

* Good, because …
* Bad, because …

## More information

Links to spec sections, stories and related ADRs.
```
