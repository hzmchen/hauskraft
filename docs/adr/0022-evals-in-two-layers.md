---
status: Proposed
date: 2026-10-24
---

# Evals in two layers: free scripted tests in CI, real-model evals on demand

## Context and problem statement

The assistant's behaviour depends on the system prompt, the tool definitions, the skills and the model. A change to
any of them can break workflows without a single unit test failing, and a model that works today can be replaced
tomorrow. Real-model runs cost money and are not deterministic, so they can't gate every pull request. How do we get
rigour without making CI expensive or flaky?

## Decision drivers

* Every PR proves the harness logic (gate, confirmation, tool selection, usage, privacy) deterministically and for
  free.
* Prompt, tool and skill changes get measured against a real model before they ship.
* Results must be comparable across runs: same cases, same thresholds, versions recorded.
* Nothing overblown.

## Considered options

* Two layers: scripted models and a fake OpenAI-compatible server in CI; Pydantic Evals against a real endpoint on demand
* Real-model evals in every CI run
* Manual testing only

## Decision outcome

Chosen option: "Two layers", decided with the project owner on 2026-10-24.

* **Layer 1, every PR.** Unit tests use Pydantic AI's `TestModel` and `FunctionModel`. Live and Playwright tests run
  against a fake OpenAI-compatible server (`tests/fixtures/fake-llm/`) that answers from scripted scenarios and records
  every request, so tests can check what the harness sent (tools, system prompt, key) and what it did.
* **Layer 2, on demand.** `evals/` uses Pydantic Evals against a real endpoint set by `HAUSKRAFT_EVAL_BASE_URL`,
  `HAUSKRAFT_EVAL_API_KEY` and `HAUSKRAFT_EVAL_MODEL`:
  * datasets in YAML per use case: `chat-tasks`, `add-from-text` (including prompt-injection cases), `weekly-overview`
    and `safety`;
  * each case is a household fixture (tasks, date, time zone, language), an input and expectations;
  * evaluators check deterministic facts first (database state, tool calls and arguments, whether the run paused, the
    answer's language); an LLM judge with a rubric is used only for the overview's quality;
  * each case runs three times; thresholds per dataset (`safety` 100%, the others at least 90%);
  * a token cap per eval run;
  * the report (markdown and JSON) names the model, `prompt_version`, `tools_hash`, skill versions, pass rates,
    tokens, estimated cost and latency; baselines can be committed per model and compared.
* **When.** `just eval` locally, or the `evals` workflow (`workflow_dispatch`, with repository secrets). A free CI
  check comments "eval recommended" on PRs that change prompts, tool definitions or skills. Plugin skills bring their
  own eval files, which the runner discovers.

### Consequences

* Good, because CI stays free and deterministic while real behaviour is still measured before releases.
* Good, because reports tie every result to the exact prompt, tools and model.
* Bad, because a PR can merge without a real-model run. The eval-recommended comment and the release checklist cover
  that; nightly runs can follow once costs are known.
* Bad, because the fake server's scenarios must be kept in step with the tests that use them.

## More information

Spec §8.0, §13.3; ADR 0014, ADR 0019, ADR 0023; stories M2S-E01-01, M2S-E09-01 to M2S-E09-03.
