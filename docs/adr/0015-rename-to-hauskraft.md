---
status: Accepted
date: 2026-10-21
---

# Rename HearthOS to Hauskraft

## Context and problem statement

HearthOS was a working name (spec D6). Hearth Display sells a family organiser in the same space and has filed the US marks HEARTH and HEARTH DISPLAY. The repository is about to go public, so the name has to change first. The name is built into contract identifiers: packages, plugin and theme IDs, the manifest key, event types, environment variables and schema URLs. Those become breaking changes once outside plugin authors depend on them; nothing outside this repository depends on them yet.

## Decision drivers

* No trademark conflict for software in Germany, the EU or the US.
* Free domain, GitHub, npm and PyPI names.
* A domain we control for reverse-DNS IDs and schema URLs.
* Rename once, before the first public release.

## Considered options

* Hauskraft, with the namespace `dev.hauskraft`
* Châtelaine or Châtelaine Central, with `org.chatelaine`
* Tomte's Tome
* Famulus Folio

## Decision outcome

Chosen option: "Hauskraft", with the namespace `dev.hauskraft` on the domain hauskraft.dev, because every package name and handle is free and no registered mark covers software. The repository becomes `hzmchen/hauskraft`.

| Before | After |
|---|---|
| HearthOS | Hauskraft |
| `@hearthos/*` | `@hauskraft/*` |
| `hearthos_core`, `hearthos_sdk`, `hearthos_tasks` | `hauskraft_core`, `hauskraft_sdk`, `hauskraft_tasks` |
| `org.hearthos.*` | `dev.hauskraft.*` |
| `hearthos.plugin.json`, `hearthos_api` | `hauskraft.plugin.json`, `hauskraft_api` |
| `hearthos.task.created` and the other event types | `hauskraft.task.created` and so on |
| `HEARTHOS_*` | `HAUSKRAFT_*` |
| `https://hearthos.dev/schema/…`, `https://schemas.hearthos.org/events/…` | `https://hauskraft.dev/schema/…`, `https://hauskraft.dev/schema/events/…` |
| `https://hearthos.dev/problems/…` | `https://hauskraft.dev/problems/…` |
| `--hearth-*`, `data-hearth-*` | `--hauskraft-*`, `data-hauskraft-*` |
| CLI `hearthos`, cookie `hearthos_session`, demo password `hearthos-demo` | `hauskraft`, `hauskraft_session`, `hauskraft-demo` |

### Consequences

* Good, because identifiers and schema URLs now sit under a domain we own, and the two schema hosts become one.
* Good, because no compatibility aliases are needed: nothing outside the repository used the old names.
* Bad, because local databases, sessions and browser settings reset once, since IDs and event types are stored.
* Bad, because the name does not survive English dictation (it comes out as "Housecraft"), and German smart-home users may read it as home energy ("Hauskraftwerk"). A German mark HAUSKRAFT covers electrical switches and sockets, not software. The spec owner accepted these trade-offs.
* ADRs 0001–0014 were updated for names only; their decisions are unchanged.

## More information

Spec D10 (supersedes D6) and §14. Availability, trademark and dictation screen of 2026-10-21.
