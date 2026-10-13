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

## Added during implementation (unsorted)

- E01-05 devcontainer not verified in VS Code/Codespaces (manual checklist in PR #8).
- E02-01: 'failing any job blocks merge' needs branch protection on main with required checks lint, typecheck, unit-py, unit-web, acceptance, links (repo admin; token has no Administration permission).
- E02-05: denylist covers only the 4 versions in the story; GHSA-g7cv-rxg3-hmpx lists 84 versions across 42 @tanstack packages. Add the full list to scripts/check-denylist.mjs.
- E06-01: tests/acceptance/schemas/test_manifest_schema.py::test_real_tasks_manifest_passes carries both M0S-E06-01 (module pytestmark) and M0S-E07-01. It xfails until E07-01 adds the tasks manifest, so the suite prints 'BROKEN M0S-E06-01' although every E06-01-only test passes. The spec owner may want the module mark scoped to the E06-01 tests. Same pattern elsewhere: one test tagged with two stories passes only when both are built.
- E10-01: two schema URL domains are in use: hearthos.dev/schema/... (manifest, theme, envelope) and schemas.hearthos.org/events/.../v1.json (event dataschema, from the E10 envelope contract). I kept both as specified; pick one before publishing schemas.
- E10-01/E13-04: settings.theme_changed.data.schema.json was added in E10-01 (spec says E13-04) so the cross-tagged fixture test passes for E10-01; E13-04 only needs to emit it.
- E13-01: the AC says theme.json may contain no key named css/script/style/html 'anywhere', but the contract itself defines fonts[].style and components.checkbox.style. The schema closes every object instead, so such keys are rejected everywhere except those two defined fields.

## Stories implemented but not yet flipped to green

- M0S-E03-03 (needs E07-03 for test_validation_error_is_problem_json)
- M0S-E03-02 (readyz live test needs the theme check from E13-03; e2e demo too)
- M0S-E05-01 (live tests go through POST /users, E05-05)
- M0S-E05-02: work in progress on branch m0s/e05-02-login-sessions (tests pass, 2 mypy errors left, no PR yet)
