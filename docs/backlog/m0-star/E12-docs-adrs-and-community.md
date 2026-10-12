# E12 · Docs, ADRs & community

**Goal:** Agent and community scaffolding, recorded decisions and clean licensing.
**Dependencies:** E01.

---

## M0S-E12-01 · AGENTS.md
- **Story:** As a coding agent, I want explicit repo rules, so that my PRs fit the architecture on the first try.
- **AC:** Given root `AGENTS.md` (content: `A1-agents-md-draft.md`), it is under 300 lines and links to the spec, the ADRs, the backlog and `docs/testing/README.md`, and describes the red/green loop. Nested `plugins/official/tasks/AGENTS.md`, `apps/web/AGENTS.md`, `packages/ui/AGENTS.md` and `themes/AGENTS.md` add only local specifics.
- **Tech:** The draft is already committed as the root `AGENTS.md`; this story adds the nested files and keeps the root file in sync with the ADRs.
- **Tests:** `tests/acceptance/repo/test_docs_and_licensing.py`; `tests/meta/test_docs_links.py`; CI link check (`lychee` offline mode).
- **Deps:** E01-04 · **Est:** S · **Labels:** area:docs

## M0S-E12-02 · ADRs 0001–0014
- **Story:** As a contributor, I want key decisions recorded, so that nobody relitigates them silently.
- **AC:** Given `docs/adr/`, then ADRs 0001–0014 (list: `A2-adr-index.md`) exist in MADR format with status `Accepted`, plus `docs/adr/README.md` (index and template). ADR-0013 fixes the numeric thresholds used by the theme validator (contrast pairs, destructive/primary distance, asset limits).
- **Tech:** MADR 4 template; one file per ADR named `NNNN-kebab-title.md`; index table in `docs/adr/README.md`.
- **Tests:** `tests/acceptance/repo/test_docs_and_licensing.py`.
- **Deps:** — · **Est:** M · **Labels:** area:docs

## M0S-E12-03 · Licences and community files
- **Story:** As a maintainer, I want licences and community health files, so that contributions are legally clean and welcoming.
- **AC:** Given the repo, then:
  - Root `LICENSE` is the AGPL-3.0 text and covers `services/**` and `apps/**`.
  - `packages/sdk-py`, `packages/sdk-ts`, `packages/ui`, `packages/schemas`, `plugins/official/tasks`, `themes/builtin/*`, `themes/template` and `integrations/ha-hearthos` each have an MIT `LICENSE`.
  - Bundled fonts ship with their `OFL-1.1` licence texts under each theme's `LICENSES/`; icon packs ship their own licence (Lucide ISC, Pixelarticons MIT).
  - `LICENSING.md` explains the split in plain words: core AGPL; everything plugin-facing MIT; third-party plugins and themes choose their own licence; in-process plugins may import only the MIT packages; out-of-process plugins and declarative themes are separate works; not legal advice.
  - SPDX headers are present and `REUSE.toml` covers generated and binary files.
  - `CONTRIBUTING.md` covers DCO (`git commit -s`), the story workflow, the red/green TDD loop, `just` commands, AI-assisted contribution disclosure, and the "no raw styles" rule for UI.
  - `SECURITY.md` has a private reporting route and supported versions (`main` only).
  - `CODE_OF_CONDUCT.md` is Contributor Covenant (current version, confirm at implementation).
  - Issue forms (`bug.yml`, `feature.yml`, `story.yml` mirroring the story template, `theme.yml` for theme submissions) and `pull_request_template.md` (story ID, AC checklist, tests run, screenshots in all built-in themes for UI changes, sign-off) exist.
  - `integrations/ha-hearthos/README.md` and `services/*/README.md` placeholders state "M1+, do not implement in M0*".
  - `hearthos_core/integrations/ha.py` defines a `HomeAssistantBridge` Protocol with a `NullBridge` (no network).
- **Tech:** `reuse download --all` fetches licence texts into `LICENSES/`. `LICENSE`, `LICENSES/`, `LICENSING.md` and a first `CONTRIBUTING.md` are already committed with the hand-off and only need completing.
- **Tests:** `tests/acceptance/repo/test_docs_and_licensing.py`; `reuse lint`; licence-map check (E02-04); unit test that `NullBridge` performs no I/O.
- **Deps:** E01-01 · **Est:** M · **Labels:** area:docs, legal
