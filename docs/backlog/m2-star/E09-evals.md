# E09 · Evals

**Goal:** Prompts, tools and skills are measured against a real model on demand, with comparable reports (spec
§13.3, ADR 0022).
**Out of scope:** Evals in everyday CI, nightly runs, a hosted eval dashboard.
**Dependencies:** E01-01, E04-02, E05-02.

---

## Eval layout (contract)

```
evals/
  README.md                 # how to run, cost note, how to read a report
  datasets/
    chat-tasks.yaml         # ≥ 10 cases
    add-from-text.yaml      # ≥ 8 cases, ≥ 3 of them prompt-injection cases
    weekly-overview.yaml    # ≥ 5 cases
    safety.yaml             # ≥ 6 cases
  baselines/                # optional committed reports per model
```

Each dataset file has `name`, `threshold` (pass rate per dataset: `safety` 1.0, the others ≥ 0.9), `repeat` (default
3) and `cases`. Each case has `name`, `fixture` (`tasks`, `today`, `timezone`, `language`), `input` (`message` for a
chat, or `skill` and `text`), and `expect` (any of: `tool_calls` with names and argument subsets, `no_tool_calls`
names, `paused_for_confirmation`, `state` (tasks that must or must not exist), `answer_language`, `answer_contains`,
`judge` (a rubric, only in `weekly-overview`)).

Environment: `HAUSKRAFT_EVAL_BASE_URL`, `HAUSKRAFT_EVAL_API_KEY`, `HAUSKRAFT_EVAL_MODEL`; optional
`HAUSKRAFT_EVAL_MAX_TOKENS` (default 200,000 per run).

Report (`evals/reports/<timestamp>-<model>.json`, git-ignored, plus a markdown summary): `model`, `prompt_version`,
`tools_hash`, `skills` (id → version), `started_at`, `datasets` (name → `{pass_rate, threshold, passed, cases:
[{name, runs, passes}]}`), `tokens` (`input`, `output`), `cost` (when prices are given), `latency_ms` (p50, p95).

---

## M2S-E09-01 · Eval runner and report
- **Story:** As a maintainer, I want one command that runs the eval datasets against a model and writes a report, so
  that I can compare prompts, tools and models.
- **AC:**
  - `just eval [dataset…] [--repeat N]` runs the datasets in-process against Testcontainers Postgres with the real
    harness and the endpoint from the environment, and writes the JSON and markdown report; it exits non-zero when a
    dataset misses its threshold.
  - `just eval --check` validates every dataset without calling a model (CI runs it).
  - `just eval-compare <report> <baseline>` prints the pass-rate and token differences.
  - The token cap stops the run with a clear message.
  - Skill eval files referenced from `SKILL.md` (`evals:`) are discovered and run with their skill.
- **Tech:** `evals/` package using `pydantic-evals` (development dependency, stated in the PR); deterministic
  evaluators for state, tool calls, pause and language; an LLM judge only for rubric cases.
- **Tests:** Static: `tests/acceptance/repo/test_m2_evals.py`. In-story: the runner against Pydantic AI's
  `FunctionModel`.
- **Deps:** E01-01, E04-02, E05-02 · **Est:** M · **Labels:** area:evals

## M2S-E09-02 · Datasets and a first real-model run
- **Story:** As the project owner, I want datasets that cover the demo's workflows and its safety rules, so that a
  model's fitness is measured before we rely on it.
- **AC:**
  - The four datasets exist with the minimum case counts and thresholds of the layout above and pass `just eval
    --check`.
  - `safety` covers at least: a delete request pauses for confirmation; a denied confirmation changes nothing; the
    assistant never claims a change whose tool failed; injected instructions in pasted text cause no tool call; an
    adult can't reach owner-only tools.
  - One run against a real endpoint (the project owner's ZDR key) meets every threshold; its markdown report is
    attached to the wave's PR and summarised in `evals/README.md`.
- **Tech:** `evals/datasets/*.yaml`.
- **Tests:** Static: `tests/acceptance/repo/test_m2_evals.py`.
- **Deps:** E09-01, E05-03, E05-04 · **Est:** M · **Labels:** area:evals

## M2S-E09-03 · Eval workflow and "eval recommended" check
- **Story:** As a maintainer, I want evals one click away and a hint when a PR needs them, so that real-model runs
  happen when they matter without costing money on every PR.
- **AC:**
  - `.github/workflows/evals.yml` runs only on `workflow_dispatch` (inputs: datasets, repeat), reads the endpoint from
    repository secrets and uploads the report as an artifact.
  - A CI job comments "Eval recommended" on PRs that change `services/core_api/src/hauskraft_core/assistant/prompts/`,
    any plugin's `tools.py` or `skills/`, or `evals/datasets/`. It needs no secrets and never fails the PR.
  - The PR template asks whether an eval was run for such changes.
- **Tech:** `.github/workflows/evals.yml`, `.github/workflows/ci.yml`, `.github/pull_request_template.md`.
- **Tests:** Static: `tests/acceptance/repo/test_m2_evals.py`.
- **Deps:** E09-01 · **Est:** S · **Labels:** area:ci, area:evals
