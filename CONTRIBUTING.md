# Contributing

Thanks for helping. Hauskraft is built story by story from the backlog, test-first. Please also read the [code of conduct](CODE_OF_CONDUCT.md); security problems go through [SECURITY.md](SECURITY.md), never a public issue.

## The workflow
1. Pick a story from [docs/backlog/m0-star/](docs/backlog/m0-star/README.md) whose dependencies are merged.
2. Work **red → green → refactor** as described in [AGENTS.md](AGENTS.md) and [docs/testing/README.md](docs/testing/README.md):
   run the story's acceptance tests and see them fail, write your own tests first, implement, refactor, then flip the story to green in `tests/story-status.json`.
3. Open one PR per story, titled `[M0S-Exx-yy] …`, from a branch named like `m0s/e07-02-tasks-crud`, with conventional commits (`test(M0S-E07-02): red …`, `feat(…)`, `refactor(…)`). The red commit comes before the green one. Fill in the PR template.

### The red/green loop in commands
```sh
python -m pytest tests --story M0S-E07-03            # RED: the story's spec-owned tests fail (raw mode)
python -m pytest tests --story M0S-E07-03 --live     # with the stack running
# write your own unit/integration tests, watch them fail, commit: test(M0S-E07-03): red …
# implement until green, commit: feat(M0S-E07-03): …; refactor with everything green
python scripts/backlog_tools.py coverage --write     # after flipping the story to "green" in tests/story-status.json
python scripts/backlog_tools.py check
python -m pytest tests --strict-status               # what CI runs
```

## Setup and `just` commands
Toolchain: Python 3.13 via [uv](https://docs.astral.sh/uv/), Node 24 with pnpm (version pinned in `package.json`), Docker with Compose. Run `just setup` once, then:

| Command | What it does |
|---|---|
| `just check` | lint + typecheck + unit tests; run before every push |
| `just lint` / `just fmt` / `just typecheck` | ruff, ESLint, Prettier, mypy, `tsc` |
| `just test` / `just test-int` / `just contract` | unit, integration (Testcontainers Postgres), contract tests |
| `just acceptance` | the spec-owned suite with `--strict-status` |
| `just e2e` / `just invariance` | Playwright demo script and theme invariance |
| `just gen` | regenerate OpenAPI, the TS client, the plugin registry and theme types (never edit generated files) |
| `just dev` / `just db` / `just demo` | local dev servers, the database, the full Compose demo |
| `just themes-validate` | validate the built-in themes |

Without `just`, the same commands are in the `justfile`.

## Rules that save review time
- Spec-owned tests under `tests/acceptance/`, `tests/e2e/` and `tests/fixtures/` are not changed in story PRs. If one looks wrong, say so in the PR.
- No raw styles in UI code: use `@hauskraft/ui` primitives and semantic tokens only (no colour literals, palette classes or arbitrary values). The lint rule `hauskraft/no-raw-styles` enforces it.
- Themes are data only and never change functions: no added, removed, renamed or reordered controls (spec §10.2.2).
- User-facing strings exist in English and German.
- New dependencies come with a lockfile update and a reason in the PR.

## Licences and headers
Core (`services/**`, `apps/**`) is AGPL-3.0-or-later; everything plugin-facing is MIT (see [LICENSING.md](LICENSING.md)). <!-- REUSE-IgnoreStart -->
Start new source files with an SPDX header for the folder's licence, e.g. `# SPDX-License-Identifier: MIT`.
<!-- REUSE-IgnoreEnd -->
 Files that cannot carry a comment (JSON, images, fonts) are covered by `REUSE.toml`. `reuse lint` runs in pre-commit and CI.

## Sign-off (DCO)
Sign every commit: `git commit -s`. This certifies the [Developer Certificate of Origin](https://developercertificate.org/). There is no CLA.

## AI-assisted contributions
AI coding agents are welcome and expected. Say in the PR which parts were AI-generated, make sure a human has read the diff, and follow [AGENTS.md](AGENTS.md). The human who signs off is responsible for the contribution.
