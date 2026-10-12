# M0* implementation: open questions and decisions to confirm

Collected while implementing the M0* backlog. Each entry names the story, what I did for now, and what needs a human decision. Nothing here blocks the build; the current choice is reversible.

| # | Story | Question | What I did for now |
|---|---|---|---|
| 1 | M0S-E01-01 | The story says to *move* the acceptance-suite pins out of `tests/requirements.txt` but also to leave `tests/` untouched. | Mirrored the pins into the root `dev` dependency group and kept `tests/requirements.txt` for pip-only runs. Delete the file once nobody uses pip for the suite. |
| 2 | M0S-E01-02, M0S-E01-03 | The spec-owned suite (`tests/acceptance`, `tests/meta`, `tests/_support`, `tests/conftest.py`) and `scripts/backlog_tools.py` have 91 findings under the story's ruff rule set, and AGENTS.md forbids editing them. | Excluded them from ruff and Prettier. If the spec owner wants them linted, they need a formatting pass first. |
| 3 | M0S-E12-02 | ADR-0013 was asked to confirm the proposed theme thresholds. | Confirmed them unchanged (4.5:1 text, 3:1 non-text, OKLab 0.15, 2 MB / 10 MB, 8 fonts, 500 symbols). Change the ADR if you want different numbers. |
| 4 | M0S-E12-03 | `SECURITY.md` and `CODE_OF_CONDUCT.md` need a private reporting route; there is no project email address. | Both point to GitHub private vulnerability reporting. **Needs a repo admin:** enable it under Settings → Code security → Private vulnerability reporting. Consider a dedicated contact address for code-of-conduct reports before going public. |
| 5 | M0S-E12-03 | Which licence applies to root-level docs (`README.md`, `AGENTS.md`, …) and lockfiles? `LICENSING.md` only lists `docs/**`. | `REUSE.toml` licenses root docs as MIT (like `docs/**`) and lockfiles/root tooling as AGPL-3.0-or-later (repo root). |
| 6 | M0S-E12-03 | Contributor Covenant "current version" | Used 3.0 (CC-BY-SA-4.0) with its suggested enforcement ladder as our policy. |
