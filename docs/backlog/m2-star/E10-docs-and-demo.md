# E10 · Docs & demo

**Goal:** Owners know how to set up and govern the assistant, plugin authors know how to expose tools and skills well,
and the M2* demo runs end to end on every PR.
**Out of scope:** Translated docs, video walkthroughs.
**Dependencies:** all other epics.

---

## M2S-E10-01 · Assistant docs for owners
- **Story:** As an owner, I want a short page about the assistant, so that I can set it up and know what it can see
  and do.
- **AC:**
  - `docs/assistant.md` covers: choosing an endpoint (cloud with zero data retention, or local), setting it up and
    testing it, what encryption at rest protects and what it doesn't (ADR 0021), re-entering the key outside
    production, which data the model sees (tool results and the context block; chats are private), confirmations and
    Undo, switching tools off, reading the usage page, and what is not there yet (§ Deferred of the backlog).
  - `README.md` links it; `docs/how-to-test.md` gains the M2* steps with the fake model.
- **Tech:** docs only.
- **Tests:** Static: `tests/acceptance/repo/test_m2_docs.py`.
- **Deps:** E07-03, E06-04 · **Est:** S · **Labels:** area:docs

## M2S-E10-02 · Guide for plugin authors: tools, skills, evals
- **Story:** As a plugin author, I want rules for good tools and skills, so that my plugin works well with small and
  large models.
- **AC:**
  - `docs/plugins/tools-and-skills.md` covers: the manifest and `ToolSpec`, annotations and why missing ones count as
    destructive, few coarse tools instead of many fine ones, short descriptions, enums, flat parameters, compact
    outputs with capped lists, the token budget, problem codes the model can act on, Undo and preview, agent guidance,
    the `SKILL.md` format, untrusted input in skills, and writing eval cases.
  - The tasks plugin is the worked example.
- **Tech:** docs only.
- **Tests:** Static: `tests/acceptance/repo/test_m2_docs.py`.
- **Deps:** E02-04, E05-01, E09-02 · **Est:** S · **Labels:** area:docs

## M2S-E10-03 · M2* demo script green
- **Story:** As the project owner, I want the M2* demo automated end to end, so that "the assistant works safely" is
  proven on every PR.
- **AC:**
  - `tests/e2e/agentic.spec.ts` (steps 1–12) and `tests/e2e/assistant.spec.ts` pass in CI against the fake model; the
    M0* and M1* demos still pass.
  - `CHANGELOG.md` has an M2* section; `README.md` describes the assistant.
- **Tech:** whatever the demo still needs.
- **Tests:** `tests/e2e/agentic.spec.ts`, `tests/e2e/assistant.spec.ts`, `tests/acceptance/repo/test_m2_docs.py`.
- **Deps:** E06-04, E06-05, E06-06, E07-02, E07-03, E10-01 · **Est:** M · **Labels:** area:deploy
