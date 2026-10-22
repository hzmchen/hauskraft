# Hauskraft

A Home Assistant–centred, plugin-first household cockpit: one themeable dashboard for a busy family, with governed AI help that prepares and drafts while people approve anything consequential. Self-hosted, local-first, open source.

> **Status: M0\* is done; M1\* "Household basics" is next.** M0\* (61 stories) delivered the scaffolding MVP below. M1\* (35 stories, spec v0.3) makes Hauskraft usable by a real household: first-run setup in the browser, owner and adult roles, members, accounts and household settings. Its spec-owned acceptance tests are written and red until the stories are built. Hauskraft was called HearthOS until October 2026 (ADR 0015).

## Start here

| If you want to… | Read |
|---|---|
| Understand the product and architecture | [docs/spec/hauskraft-spec-v0.3.md](docs/spec/hauskraft-spec-v0.3.md) |
| See what M1\* delivers and in which order | [docs/backlog/m1-star/README.md](docs/backlog/m1-star/README.md) |
| See what M0\* delivered | [docs/backlog/m0-star/README.md](docs/backlog/m0-star/README.md) |
| Implement a story (human or AI agent) | [AGENTS.md](AGENTS.md), then the story's epic file |
| Run or extend the tests | [docs/testing/README.md](docs/testing/README.md) |
| See which tests cover which story | [docs/testing/traceability.md](docs/testing/traceability.md) |
| Licensing | [LICENSING.md](LICENSING.md) |

## How this repo is meant to be used

Development is test-driven, one story at a time:

1. Run the story's acceptance tests and see them fail (**red**).
2. Write the unit tests for your code, then the code, until everything passes (**green**).
3. Refactor, then flip the story to green in `tests/story-status.json`.

```sh
python -m pip install -r tests/requirements.txt
python -m pytest tests                      # docs checks pass; story tests show as expected failures
python -m pytest tests --story M1S-E02-01   # one story, in raw mode
python scripts/backlog_tools.py check       # backlog, spec references, story status, coverage
```

Wave 0 of the M1\* backlog (permission table, event schemas, fresh test stack) is the place to begin.

## What M0\* gives you

`docker compose up`, log in as `demo`, and use a shared household task list on a Today dashboard, built as the first native plugin. Switch the whole household between three built-in themes (Default, Paper, Hackspace) without any function moving, while each device keeps its own light or dark mode. German and English UI.

## What M1\* adds

A household can start without demo data: a setup wizard creates the household and its first owner, who adds the other members with temporary passwords. Everyone manages their own name, language, password and signed-in devices; owners manage members, household settings and the theme, and every change to who can act shows in Activity. Home Assistant, the AI gateway, approvals and third-party connectors come later, one milestone at a time.

## Licence

Core (`services/`, `apps/`): AGPL-3.0-or-later. Everything plugin-facing (SDKs, schemas, UI kit, official plugins, themes, tests): MIT. Details in [LICENSING.md](LICENSING.md).
