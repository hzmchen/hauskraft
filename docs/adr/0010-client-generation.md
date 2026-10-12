---
status: Accepted
date: 2026-10-12
---

# API client generation with hey-api

Status: Accepted

## Context and problem statement

The web shell and plugin web packages need a typed client for the core API. Ad-hoc `fetch` calls drift from the contract.

## Decision drivers

* Types and query helpers generated from the committed OpenAPI file.
* TanStack Query integration.
* CSRF header and cookies handled in one place.

## Considered options

* `@hey-api/openapi-ts` with the TanStack Query plugin
* openapi-typescript + hand-written hooks
* Orval

## Decision outcome

Chosen option: "`@hey-api/openapi-ts`" with an **exact** version pin (the project is pre-1.0) and the `@hey-api/typescript`, `@hey-api/sdk` and `@tanstack/react-query` plugins, using `@hey-api/client-fetch` with `credentials: 'include'` and a CSRF interceptor. Output goes to `packages/sdk-ts/src/client` and is never edited by hand; `just gen` regenerates it and CI fails on drift.

### Consequences

* Good, because UI code uses generated query options instead of ad-hoc fetch
* Good, because contract changes surface as type errors
* Bad, because pre-1.0 releases may change output; upgrades are deliberate and reviewed

## More information

Stories M0S-E03-05, M0S-E06-05.
