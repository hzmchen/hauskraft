---
status: Accepted
date: 2026-10-12
---

# Record architecture decisions

Status: Accepted

## Context and problem statement

Hauskraft is built largely by coding agents working story by story. Without a written record, decisions about seams, schemas and the theme contract get relitigated or silently changed by whoever touches the code next.

## Decision drivers

* Agents need a stable, citable source for why things are the way they are.
* Contracts (OpenAPI, JSON Schemas, theme tokens) must not drift without review.
* The format should be lightweight and reviewable in a pull request.

## Considered options

* MADR files in `docs/adr/`
* Decisions only in the spec
* Wiki or issue tracker

## Decision outcome

Chosen option: "MADR files in `docs/adr/`", because they live next to the code, are reviewed in the same PR as the change, and MADR 4 is a small, widely known template. An ADR is **required** for any change to a seam (`authorize()`, plugin loader, outbox, `IdentityProvider`), a schema in `packages/schemas`, or the theme contract (tokens, variants, layout options). Accepted ADRs are never rewritten, only superseded.

### Consequences

* Good, because reviewers and agents can cite a numbered decision instead of re-arguing it
* Good, because contract changes become visible in review
* Bad, because writing ADRs costs time on small changes; the rule is limited to seams, schemas and the theme contract to keep it proportionate

## More information

Index and template: [README.md](README.md). Spec §13.4 (contribution model).
