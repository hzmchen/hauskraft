# Testing and validation

Hauskraft is built test-first: **red, green, refactor**, one story at a time (ADR-0014). This page explains the suite that already exists before any product code, how to run it, and how a story moves from red to green.

## What is in `tests/`

| Layer | Folder | Talks to | Needs | Example |
|---|---|---|---|---|
| Meta (docs validation) | `tests/meta/` | spec, backlog, the suite itself | Python only | backlog IDs, deps, counts, spec `§` refs, links, traceability |
| Static contract | `tests/acceptance/{repo,schemas,web}` | files in the repo | Python only | manifest schema vs fixtures, CI workflow shape, i18n key parity |
| Tooling black box | `tests/acceptance/repo`, `web` | ruff, eslint, node scripts via stdin/CLI | workspace installed | plugins may not import core; no raw styles |
| CLI black box | `tests/acceptance/themes` | `hauskraft themes validate --json` | `hauskraft` CLI | every fixture theme gives its expected codes |
| Live API | `tests/acceptance/api` | HTTP at `HAUSKRAFT_BASE_URL` | running stack + `--live` | tasks CRUD, CSRF, theme switching |
| End to end | `tests/e2e/*.spec.ts` | the browser | running stack, Playwright | the 11-step demo script, theme invariance |
| Unit / integration | inside each package | code | written by the story | `services/core_api/tests/`, Vitest in `apps/web` |

Every test is tied to one or more backlog stories with `@pytest.mark.story("M1S-Exx-yy")` or Playwright tags (`story("M1S-Exx-yy")`). Meta tests carry `@pytest.mark.meta` instead and must always pass.

Story IDs carry their milestone: `M0S-…` for M0* (`docs/backlog/m0-star/`, done), `M1S-…` for M1* (`docs/backlog/m1-star/`, done) and `M2S-…` for M2* (`docs/backlog/m2-star/`). `scripts/backlog_tools.py` reads every `docs/backlog/m<N>-star/` folder, and `tests/story-status.json` holds the switch for all of them, so the stories of a finished milestone stay hard gates.

Fixtures in `tests/fixtures/` (manifests, events, theme packages, lockfiles, lint probes) are part of the contract. See `tests/fixtures/README.md`.

## Red and green: `tests/story-status.json`

One switch per story:

- `"red"`: not done. Its tests run and are reported as **xfail** ("RED: … not implemented yet"), so the suite stays usable while work is in progress.
- `"green"`: done. Its tests are **hard gates**: any failure fails CI.
- `"acceptance": "suite"` means spec-owned tests exist in `tests/`; `"in-story"` means the implementer writes the first tests inside the story (11 stories, mostly internal seams like migrations and SDK types).

CI runs with `--strict-status`: if every test of a red story passes, the run fails and tells you to flip the story to green. That keeps the switch honest. The current mapping is in [traceability.md](traceability.md).

## The loop for one story

```sh
# 0. once: test dependencies (later part of the uv workspace, M0S-E01-01)
python -m pip install -r tests/requirements.txt

# 1. RED: see the spec-owned tests fail for the right reason (raw mode, no xfail)
python -m pytest tests --story M0S-E07-03            # static + CLI tests
python -m pytest tests --story M0S-E07-03 --live     # plus live API tests (stack running)
HAUSKRAFT_TDD_RAW=1 pnpm --filter @hauskraft/acceptance-e2e exec playwright test --grep @M0S-E07-03

#    then write the unit/integration tests for your code and watch them fail too
#    commit: test(M0S-E07-03): red ...

# 2. GREEN: implement until everything above passes
#    commit: feat(M0S-E07-03): ...

# 3. REFACTOR with everything green
#    commit: refactor(M0S-E07-03): ...

# 4. FLIP: set "M0S-E07-03": {"status": "green", ...} in tests/story-status.json
python scripts/backlog_tools.py coverage --write
python scripts/backlog_tools.py check
python -m pytest tests --strict-status
```

Rules:

- **Never weaken a spec-owned test to get to green.** Do not edit, skip or delete files under `tests/acceptance/`, `tests/e2e/` or `tests/fixtures/` in a story PR. If a test looks wrong, stop and say so in the PR; the spec owner fixes the test (and writes an ADR if a contract changes).
- **Test black boxes.** Acceptance tests use only public surfaces: HTTP, the CLI's `--json` output, linters via stdin, and roles plus accessible names in the UI ([ui-contract.md](ui-contract.md)). Inside a package you are free; cover it with your own unit tests.
- **In-story stories** start their red step by writing the tests listed in the story's **Tests** field.

## Running everything

```sh
python -m pytest tests                       # meta + static; red stories show as xfail
python -m pytest tests --strict-status       # what CI runs on every PR

docker compose -f compose.yaml -f deploy/compose/compose.test.yaml up --wait
python -m pytest tests --live --strict-status
pnpm --filter @hauskraft/acceptance-e2e exec playwright test
```

The test overlay (`deploy/compose/compose.test.yaml`, M0S-E11-01) mounts `tests/fixtures/themes` so the live tests can select fixture themes. Environment variables: `HAUSKRAFT_BASE_URL` (default `http://localhost:8080`), `HAUSKRAFT_DEMO_PASSWORD` (default `hauskraft-demo`), `HAUSKRAFT_CLI`, `HAUSKRAFT_RUFF`, `HAUSKRAFT_ESLINT`, `HAUSKRAFT_E2E_RESTART_CMD` (step 11 of the demo), `HAUSKRAFT_TDD_RAW=1` (Playwright raw mode).

### The fresh stack (M1*)

First-run setup can only be tested on a household without accounts, so a second, unseeded stack runs next to the
demo stack (M1S-E01-01):

```sh
just fresh-up        # project hauskraft-fresh on http://localhost:8081, no demo seed, no database port
just fresh-reset     # remove its containers and database volume, then start it again (empty and healthy)

HAUSKRAFT_FRESH_BASE_URL=http://localhost:8081 HAUSKRAFT_FRESH_RESET_CMD="just fresh-reset" \
  python -m pytest tests --live --strict-status
```

Tests marked `fresh` (pytest) and the specs that use `tests/e2e/support/fresh.ts` (Playwright) run only when
`HAUSKRAFT_FRESH_BASE_URL` is set; otherwise they are skipped. `HAUSKRAFT_FRESH_RESET_CMD` is a shell command that
leaves an empty, healthy fresh stack; tests run it before each first-run scenario. The fresh stack uses the same
images as the demo stack, so build them first (`just demo`).

### The fake model (M2*)

Assistant tests never call a real provider. The test stack runs a small OpenAI-compatible server,
`tests/fixtures/fake-llm/server.py`, that answers from scripted scenarios and records every request (M2S-E01-01,
ADR 0022). Tests point the assistant at it and then check what the harness sent: the tools offered, the system prompt
and the API key.

```sh
python tests/fixtures/fake-llm/server.py --port 8090   # or: the fake-llm service of compose.test.yaml
HAUSKRAFT_FAKE_LLM_URL=http://fake-llm:8090/v1 HAUSKRAFT_FAKE_LLM_ADMIN_URL=http://localhost:8090 \
  python -m pytest tests --live --strict-status
```

`HAUSKRAFT_FAKE_LLM_URL` is the URL the API container uses (what an owner enters in Settings → Assistant);
`HAUSKRAFT_FAKE_LLM_ADMIN_URL` is the URL the tests use to read recorded requests. Its behaviour is described in
`tests/fixtures/fake-llm/README.md`; `tests/meta/test_fake_llm.py` keeps it honest. Real-model evals are separate and
run on demand (`just eval`, `evals/README.md`).

## Validating the docs

```sh
python scripts/backlog_tools.py check        # IDs, fields, deps, cycles, counts, § refs, status, coverage
python scripts/backlog_tools.py coverage     # story -> test files
```

`tests/meta/` runs the same checks plus link checking and consistency between the spec, `tests/_support/theme_contract.py`, the fixtures and the UI contract.

## What the suite pins down

Writing the tests first forced a few contracts that were implicit before. They are now in the backlog and spec:

- Readiness check names (`database`, `migrations`, `plugins`, `theme`) — E03-02.
- Theme validator issue codes, CLI exit codes and `--json` shape; exact required token names; the shapes of `tokens-v1.json`, `icon-names-v1.json` and `layout-options-v1.json` — E13 "Contracts".
- Script interfaces: `check-denylist.mjs [lockfile]`, `check-licence-map.py [--root DIR]` — E02.
- The test overlay that mounts fixture themes — E11-01.
- Accessible names and test hooks for the UI — [ui-contract.md](ui-contract.md).
- Demo step 4 now sets the due date on All tasks (the widget only edits titles).
