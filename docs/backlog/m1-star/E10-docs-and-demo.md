# E10 · Docs & demo

**Goal:** Operators know how to install for real, run the household and recover; the M1* demo script runs green.
**Out of scope:** A documentation website, release notes automation.
**Dependencies:** E01, E03, E06, E07.

---

## M1S-E10-01 · Household admin docs
- **Story:** As an operator, I want short docs for a real install and for running the household, so that I don't need
  to read the code.
- **AC:**
  - `README.md` "Quick start" has two paths: "Try the demo" (unchanged) and "Set up your household"
    (`HAUSKRAFT_SEED_DEMO=false docker compose up --wait`, open http://localhost:8080, finish setup right away).
  - `docs/household-admin.md` covers the setup wizard and its first-visitor rule, roles, members, temporary
    passwords, deactivation, household settings, `HAUSKRAFT_WEB_BIND` and TLS for LAN use, and recovery with
    `hauskraft users set-password` and `hauskraft users list` inside the `api` container.
  - `docs/how-to-test.md` lists the M1* demo steps and how to run the fresh stack.
- **Tech:** Docs only; links checked by the existing link job.
- **Tests:** `tests/acceptance/repo/test_m1_deploy_and_docs.py`.
- **Deps:** E03-02, E06-06 · **Est:** S · **Labels:** area:docs

## M1S-E10-02 · M1* demo script green
- **Story:** As the project owner, I want the M1* demo automated end to end, so that "usable household" is proven on
  every PR.
- **AC:**
  - `tests/e2e/basics.spec.ts` (spec-owned) passes steps 1–11 against the fresh stack in CI; step 12 is CI itself.
  - `tests/e2e/demo.spec.ts` (M0*) still passes on the demo stack.
  - `CHANGELOG.md` (created if it doesn't exist yet) lists M1* under `Unreleased`.
- **Tech:** No new product code expected; fixes go into the stories they belong to.
- **Tests:** `tests/e2e/basics.spec.ts`.
- **Deps:** E01-02, E03-02, E04-02, E04-04, E05-04, E06-05, E07-03, E07-04, E08-02, E09-02 · **Est:** M · **Labels:** area:deploy, type:test
