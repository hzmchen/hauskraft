<!-- SPDX-License-Identifier: MIT -->

# Evals

Evals measure how well a real model works with Hauskraft's assistant: the system prompt, the tools and the skills.
They run on demand, not in everyday CI, because every run costs money ([ADR 0022](../docs/adr/0022-evals-in-two-layers.md)).
CI runs the free layer on every PR: the harness tests against the fake model, and `just eval --check`.

## Run them

```bash
export HAUSKRAFT_EVAL_BASE_URL=https://api.openai.com/v1   # any OpenAI-compatible Chat Completions endpoint
export HAUSKRAFT_EVAL_API_KEY=…                             # a dedicated key with a spend limit
export HAUSKRAFT_EVAL_MODEL=gpt-…                           # the model households would use
just eval                      # every dataset, each case 3 times (the dataset's `repeat`)
just eval chat-tasks safety    # some datasets
just eval safety --repeat 1    # a quick look
just eval --check              # validate the datasets; no model is called
```

Optional settings:

- `HAUSKRAFT_EVAL_MAX_TOKENS` (default 200,000) caps the tokens of one run; when it's reached the run stops with a
  message and exit code 2.
- `HAUSKRAFT_EVAL_JUDGE_MODEL` names the model that grades rubric cases (default: the evaluated model).
- `HAUSKRAFT_EVAL_PRICE_INPUT` and `HAUSKRAFT_EVAL_PRICE_OUTPUT` (per million tokens) add an estimated cost.
- `HAUSKRAFT_TEST_DATABASE_URL` uses an existing, disposable database instead of a Testcontainers Postgres.

**Cost:** a full run is about 40 cases × 3 runs, each one to four model requests of roughly 1,500 tokens: about
400,000 tokens in all. With a small model that's cents; with a large one, a few euros. The default token cap of
200,000 suits iterating on a dataset or two with `--repeat 1`; for a full run set `HAUSKRAFT_EVAL_MAX_TOKENS=600000`.
Prefer an account with zero data retention: evals send only the made-up households in the datasets, but they still
leave your machine.

The runner starts the app in-process on a fresh database, with an owner and an adult, and talks to it through the API.
Before each run of a case it resets the household to the case's fixture and fixes the prompt's "Today" to the
fixture's date. Everything else is real: the system prompt, the tools, permissions, the gate and confirmations.

## Datasets

`datasets/` holds the core datasets; plugin skills bring their own, referenced from their `SKILL.md` (`evals:`), and
the runner finds them (for example `tasks.add-from-text`).

```yaml
name: chat-tasks
threshold: 0.9 # pass rate the dataset must reach (safety: 1.0)
repeat: 3 # runs per case
cases:
  - name: adds a task with a due date
    fixture: # the household the case starts from
      tasks: [{ title: Plan the garden, due_on: 2026-11-05, done: false }]
      today: 2026-11-02
      timezone: Europe/Berlin
      language: en # the person's language
      role: owner # or adult (default owner)
    input: # a chat message (confirm: approved|denied answers a confirmation) or a skill with text
      message: "Add 'Buy milk', due tomorrow"
    expect: # every key given must hold for the run to pass
      tool_calls: [{ name: tasks.create, args: { title: Buy milk, due_on: 2026-11-03 } }] # args: a subset, any case
      no_tool_calls: [tasks.delete] # "*" for none at all
      paused_for_confirmation: false
      state: { exists: [Buy milk], missing: [], done: [], open: [Buy milk], count: 2 }
      answer_language: en # told from common words; quoted titles don't count
      answer_contains: ["(?i)milk"] # regular expressions, case-insensitive
      judge: "…" # a rubric for an LLM judge; only for the weekly overview's quality
```

For skills with typed output (`add-from-text`), the answer the checks read is one `title | due_on` line per suggested
task, with `-` for no date.

## Read a report

Each run writes `evals/reports/<time>-<model>.json` and `.md` (git-ignored). The report names the model, the
`prompt_version` (a hash of the prompt files), the `tools_hash` and the skill versions, so two reports are comparable
only when you know what changed. It lists the pass rate per dataset against its threshold, the passes per case, the
reasons for every failed run, tokens, the estimated cost and the latency per run (p50, p95).
`just eval` exits 1 when a dataset misses its threshold.

```bash
just eval-compare evals/reports/new.json evals/baselines/gpt-x.json   # pass-rate and token differences
```

Commit a report to `evals/baselines/` when it should be the reference for a model.

## When to run them

Run the evals before merging a change to the system prompt (`services/core_api/src/hauskraft_core/assistant/prompts/`),
a tool's definition (any plugin's `tools.py`), a skill (`skills/`) or a dataset, and say in the PR what you ran. CI
comments "Eval recommended" on such PRs. Maintainers can also run them from GitHub: Actions → evals → Run workflow. The workflow reads
`HAUSKRAFT_EVAL_BASE_URL` and `HAUSKRAFT_EVAL_MODEL` from the repository variables (Settings → Secrets and variables →
Actions → Variables) and `HAUSKRAFT_EVAL_API_KEY` from the repository secrets; for a full run, enter `600000` as
max_tokens.
