# E01 · Repo & tooling

**Goal:** A reproducible monorepo where a contributor or agent can run `just setup && just check` on a fresh machine.
**Out of scope:** Nx/Turborepo, release automation.
**Dependencies:** none.

---

## M0S-E01-01 · Monorepo skeleton and workspaces
- **Story:** As a contributor, I want the spec directory layout with uv and pnpm workspaces, so that every package resolves from one lockfile per ecosystem.
- **AC:**
  - Given a fresh clone, when I run `uv sync --all-packages` and `pnpm install --frozen-lockfile`, then both succeed.
  - `uv run python -c "import hearthos_core, hearthos_sdk, hearthos_tasks"` works.
  - `pnpm -r exec tsc --noEmit` succeeds for `apps/web`, `packages/sdk-ts`, `packages/ui` and `plugins/official/tasks/web`.
- **Tech:**
  - Root `pyproject.toml` `[tool.uv.workspace] members = ["services/core_api","packages/sdk-py","plugins/official/tasks/backend"]`; `.python-version` = `3.13`.
  - `pnpm-workspace.yaml`: `apps/*`, `packages/sdk-ts`, `packages/ui`, `plugins/official/*/web`, `tests/e2e`; `.node-version` = `24`. Use `"packageManager"` in `package.json`.
  - Move the pins from `tests/requirements.txt` into the root `dev` dependency group so `uv run pytest tests` works; keep `tests/` untouched otherwise.
  - Create `themes/builtin/` and `themes/template/` folders (data only, not workspace packages).
  - Placeholder READMEs for later services as in the README tree.
- **Tests:** CI smoke job runs the import and `pnpm -r exec tsc --noEmit`.
- **Deps:** — · **Est:** S · **Labels:** area:repo, type:chore

## M0S-E01-02 · Python tooling config
- **Story:** As a coding agent, I want ruff, mypy and pytest configured once at the root, so that I get consistent feedback in every package.
- **AC:** Given any Python package, when I run `just lint` and `just typecheck`, then ruff (check + format --check) and mypy `--strict` run over all members with zero findings on the skeleton.
- **Tech:**
  - ruff `0.17.x`: rules `E,F,I,UP,B,S,ASYNC,PT,RUF,TID`. Use `flake8-tidy-imports.banned-api` to ban `hearthos_core` imports from `plugins/**`.
  - mypy `2.4.x` with the `pydantic.mypy` plugin. pytest `9.1` with `asyncio_mode=auto` (pytest-asyncio 1.4) and markers `unit`, `integration`, `contract`.
  - Optional: a non-blocking `ty check` job.
- **Tests:** A deliberately bad import in a fixture file is caught by a ruff test (`tests/tooling/test_banned_imports.py` runs ruff via subprocess).
- **Deps:** E01-01 · **Est:** S · **Labels:** area:repo

## M0S-E01-03 · TypeScript tooling config
- **Story:** As a coding agent, I want shared tsconfig, ESLint and Prettier, so that web, sdk-ts, ui and plugin web code follow one standard.
- **AC:**
  - Given the web workspace, when I run `pnpm lint && pnpm typecheck`, then ESLint 9 flat config (typescript-eslint, react-hooks, jsx-a11y) and `tsc --noEmit` pass.
  - An import from `apps/web/**` inside `plugins/**/web` fails lint.
  - Inside `plugins/**/web`, imports are allowed only from `@hearthos/sdk-ts`, `@hearthos/ui`, `react`, `react-dom`, `react-i18next` and `@tanstack/react-query`.
- **Tech:**
  - Pin `typescript@~6.0` (ADR-0011). Root `tsconfig.base.json` with `strict`, `moduleResolution: bundler` and `verbatimModuleSyntax`.
  - ESLint `no-restricted-imports` implements the allowlist. The raw-style lint rule is added in E13-08.
- **Tests:** Lint fixture test.
- **Deps:** E01-01 · **Est:** S · **Labels:** area:repo

## M0S-E01-04 · justfile and pre-commit
- **Story:** As a contributor, I want one task runner, so that I don't need to memorise per-package commands.
- **AC:** Given the repo, when I run `just --list`, then I see `setup, dev, db, lint, fmt, typecheck, test, test-int, contract, gen, e2e, invariance, acceptance, demo, themes-validate, check`. `pre-commit run -a` passes.
- **Tech:**
  - `just dev` runs `docker compose up db -d`, then `uvicorn hearthos_core.app:create_app --factory --reload` and `pnpm --filter web dev`; Vite proxies `/api` to `:8000`.
  - `just acceptance` runs `python -m pytest tests --strict-status` (add `--live` with the stack running).
  - `just themes-validate` runs `hearthos themes validate` over `themes/builtin/*` (wired up in E13-09).
  - `.pre-commit-config.yaml`: ruff, ruff-format, prettier, check-json/yaml, end-of-file-fixer, `reuse lint`.
- **Tests:** A CI job runs `pre-commit run -a`.
- **Deps:** E01-02, E01-03 · **Est:** S · **Labels:** area:repo

## M0S-E01-05 · Devcontainer (optional)
- **Story:** As a new contributor, I want a devcontainer, so that I can start in one click.
- **AC:** Given VS Code or Codespaces, when the container opens, then `just setup && just check` passes.
- **Tech:** `.devcontainer/devcontainer.json` with Python 3.13, Node 24, docker-in-docker and the uv feature.
- **Tests:** Manual checklist in the PR.
- **Deps:** E01-04 · **Est:** S · **Labels:** area:repo, optional
