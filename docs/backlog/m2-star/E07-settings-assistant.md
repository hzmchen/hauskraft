# E07 · Settings → Assistant

**Goal:** Owners connect, check and govern the assistant on one settings page (spec §8.0, §10.1).
**Out of scope:** Limits, several endpoints, voice endpoints, per-member tool rules.
**Dependencies:** E03, E02-03, E08-02.

The section "Assistant" comes after Members in the settings navigation and is shown to owners only; adults are
redirected to Appearance from its URL (as for Household and Members in M1*). Names are in
`docs/testing/ui-contract.md` § "M2* additions".

---

## M2S-E07-01 · Endpoint form and connection test
- **Story:** As an owner, I want to enter and test the model endpoint in the browser, so that I can set up the
  assistant without files or restarts.
- **AC:**
  - `/settings/assistant` shows the heading "Assistant" and the region "Endpoint" with the textboxes "Base URL" and
    "Model", the password field "API key" (exact label; after saving, the hint "Saved key ends in <last four>"; empty
    means keep), the combobox "Model location" (Cloud, Local) and the buttons "Save endpoint" (then "Endpoint saved")
    and "Test connection".
  - "Test connection" shows the list "Connection checks" with "Server reachable", "API key accepted", "Model found" and
    "Tool calls supported", each followed by ": OK" or ": Failed".
  - `api_key_status: "needs_reentry"` shows "Enter the API key again: the server's secret changed."
  - "Remove endpoint" asks in the alert dialog "Remove the endpoint?" (Remove, Cancel) and clears it.
  - Validation errors appear next to their field.
- **Tech:** `apps/web/src/routes/_app/settings.assistant.tsx`, `settings/sections.ts`.
- **Tests:** E2E: `tests/e2e/agentic.spec.ts` step 1, `tests/e2e/assistant.spec.ts`. Vitest: form states.
- **Deps:** E03-04 · **Est:** M · **Labels:** area:web

## M2S-E07-02 · Tool switches
- **Story:** As an owner, I want to switch individual tools off, so that the assistant can't do what we don't want it
  to.
- **AC:**
  - The region "Tools" lists every tool from `GET /assistant/tools` as a switch named by the tool (e.g.
    "tasks.delete"), with its description and its annotations in words ("Reads only", "Changes data", "Deletes – asks
    first").
  - Switching saves `tools_disabled` immediately and shows "Tools saved".
- **Tech:** the same route.
- **Tests:** E2E: `tests/e2e/agentic.spec.ts` step 11.
- **Deps:** E07-01, E02-03 · **Est:** S · **Labels:** area:web

## M2S-E07-03 · Usage page
- **Story:** As an owner, I want to see how many tokens the household uses, so that I can judge cost and spot misuse.
- **AC:**
  - The region "Usage" has the combobox "Period" (Today, Last 7 days, Last 30 days) and the tables "Usage by day",
    "Usage by member" and "Usage by model" with the columns Requests, Input tokens, Output tokens.
  - Requests whose tokens the server didn't report are counted and marked "unknown".
  - With prices set (textboxes "Price per million input tokens", "Price per million output tokens", button "Save
    prices"), the text "Estimated cost: <amount> EUR" shows for the period.
- **Tech:** the same route.
- **Tests:** E2E: `tests/e2e/agentic.spec.ts` step 10.
- **Deps:** E07-01, E08-02 · **Est:** M · **Labels:** area:web
