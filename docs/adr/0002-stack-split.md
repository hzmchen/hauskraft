---
status: Accepted
date: 2026-10-12
---

# Stack split: Python backend, TypeScript frontend

Status: Accepted

## Context and problem statement

Hauskraft needs a backend that speaks Home Assistant, agent frameworks and German banking, and a frontend that renders a themeable widget dashboard. Spec §4.1 compares the options.

## Decision drivers

* The HA custom integration must be Python.
* Pydantic AI and DBOS give durable human-in-the-loop agents in Python.
* German banking libraries (python-fints) are Python.
* UI, widgets, theming and MCP Apps rendering are native in TypeScript/React.
* Agents implement this code: the stack should have deep training corpora and typed contracts.

## Considered options

* Python backend + TypeScript frontend, contract-first via OpenAPI
* TypeScript everywhere (Node backend)
* Python everywhere (server-rendered UI)

## Decision outcome

Chosen option: "Python backend + TypeScript frontend". Backend: Python 3.13, FastAPI, SQLAlchemy 2.1 (async), Pydantic v2, Alembic, Postgres 16. Frontend: React 19, Vite 8, TypeScript, TanStack Router/Query, shadcn/ui on Radix and Tailwind v4 packaged as `@hauskraft/ui`. The contract between them is OpenAPI 3.1 generated from FastAPI and committed (`packages/schemas/openapi/core-api.openapi.json`); the TypeScript client is generated from it (ADR-0010).

### Consequences

* Good, because each side uses the ecosystem where it is strongest
* Good, because the committed OpenAPI file lets frontend and backend work in parallel
* Bad, because two toolchains (uv and pnpm) must be kept healthy
* Bad, because contract drift is possible and must be caught in CI (`just gen && git diff --exit-code`)

## More information

Spec §4.1; stack pins in `docs/backlog/m0-star/README.md`.
