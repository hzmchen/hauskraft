# E08 · Usage

**Goal:** Every model request is recorded, and owners can see token use per day, member, model and kind (spec §8.0,
§8.9).
**Out of scope:** Limits and budgets, export to Langfuse or Phoenix, per-request content.
**Dependencies:** E04-02.

---

## Usage API (contract)

| Method & path | Who | Query | Success | Errors |
|---|---|---|---|---|
| `GET /api/v1/assistant/usage` | owner (`assistant.usage.read`) | `from`, `to` (dates, inclusive, household time zone; default the last 30 days), `group_by` (`day`·`user`·`model`·`kind`, default `day`) | 200 `Usage` | 401, 403 `policy_denied`, 422 |

```
Usage = {from, to, group_by,
         totals: {requests, input_tokens, output_tokens, unknown_requests, cost: {amount, currency}|null},
         groups: [{key, label, requests, input_tokens, output_tokens, unknown_requests}]}
```

`key` is the date, user id, model name or kind; `label` is the date, the member's display name, the model name or the
kind. Groups are sorted by key (days ascending) or by input tokens (descending) for the others.

---

## M2S-E08-01 · Usage records
- **Story:** As an owner, I want every model request counted, so that the overview is complete.
- **AC:**
  - Each model request of a chat run, a skill run or a connection test stores: person, run, kind, model, input,
    output and cached tokens (when reported), duration, status and time. Field names follow the OpenTelemetry
    generative-AI conventions (`gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`).
  - A response without `usage` is stored with unknown tokens and counted in `unknown_requests`.
  - Deleting a chat keeps its usage rows.
  - Pydantic AI's instrumentation hook is wired up without an exporter.
- **Tech:** `assistant_usage` table, `assistant/usage.py`.
- **Tests:** Live: `tests/acceptance/api/test_assistant_usage.py`.
- **Deps:** E04-02 · **Est:** S · **Labels:** area:api, area:db

## M2S-E08-02 · Usage overview API and cost estimate
- **Story:** As an owner, I want totals by day, member, model and kind with an estimated cost, so that I can judge what
  the assistant costs.
- **AC:**
  - The contract above holds; the totals equal the sum of the groups.
  - With `prices` set (E03-02), `cost.amount` = input tokens × input price + output tokens × output price per million,
    rounded to cents; without prices `cost` is null.
  - An adult gets 403 `policy_denied`.
- **Tech:** `assistant/usage.py`.
- **Tests:** Live: `tests/acceptance/api/test_assistant_usage.py`.
- **Deps:** E08-01 · **Est:** S · **Labels:** area:api
