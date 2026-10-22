# Open admin and spec tasks

This file lives only on the `admin` branch and is never merged into `main`. Claude Code collected it on
2026-10-22. Tick items off here, or tell Claude and it updates the list.

## Do first

1. **Register hauskraft.dev.** Every schema `$id`, problem URL and plugin ID (`dev.hauskraft.*`) points at it,
   and ADR 0015 calls it "a domain we own". Until it is registered, anyone can take it.
   - Porkbun: $8.75 the first year, then $12.87 a year (prices from 2026-10-21).
   - Optional: hauskraft.app ($8.75, then $14.93) and hauskraft.eu ($5.88).
2. **Create the npm organisation `hauskraft`** (free for public packages). It reserves the `@hauskraft/*` scope
   that all our TypeScript packages use.

## GitHub settings

- [x] Ruleset on `main`: PR required, all 11 checks required.
- [x] Automatically delete head branches.
- [x] Private vulnerability reporting.
- [ ] **Secret scanning push protection.** Settings → Advanced Security → Secret Protection → Push protection →
      Enable.
- [ ] Optional: repo description, website (hauskraft.dev, once registered) and topics. All three are empty. Edit
      them with the gear icon next to "About" on the repo page.
- [ ] Optional: a contact address for code-of-conduct reports. `CODE_OF_CONDUCT.md` routes reports through private
      vulnerability reporting and sends reports about a maintainer to "the others", but there is only one
      maintainer.

## Package names (when publishing starts)

- [ ] PyPI: `hauskraft-sdk`, `hauskraft-core` and `hauskraft-tasks` were free on 2026-10-21. A name is claimed by
      its first upload, so nothing to do until there is a release workflow.
- [ ] Optional: Docker Hub `hauskraft` (free on 2026-10-21), only if images go to Docker Hub rather than GitHub's
      container registry.

## After the domain is registered (Claude, with your go)

- [ ] Choose hosting for hauskraft.dev. Suggestion: GitHub Pages from this repo with a custom domain, which needs
      a few DNS records at Porkbun.
- [ ] Publish the JSON schemas under `https://hauskraft.dev/schema/…` and the problem pages under
      `https://hauskraft.dev/problems/…`. Today these URLs don't resolve, so editors that follow `$schema` find
      nothing.

## Spec decisions (you)

- [ ] **Account menu name.** It blocks the axe-core 4.14 update (see Dependabot below).
  - **The problem:** the button at the top right shows the user's name, "Demo Adult", next to an icon. Its
    accessible name is "Account menu", which is what screen readers read out and what voice control listens for
    (`docs/testing/ui-contract.md`, de "Kontomenü"). WCAG 2.5.3 "Label in Name" requires the visible text to be
    part of that name. A voice-control user who sees "Demo Adult" and says "click Demo Adult" gets no match.
    axe-core 4.14 reports this as serious (`label-content-name-mismatch`) on every page, so `e2e` fails.
  - **Option A (recommended):** name the button with its visible text plus its purpose, for example
    "Demo Adult, account menu" (de "Demo Adult, Kontomenü"). Of the spec-owned files, only the ui-contract row
    changes. The spec-owned tests keep passing, because Playwright matches names by substring.
  - **Option B:** an icon-only button named "Account menu", with the name shown inside the menu ("Signed in as
    Demo Adult"). The ui-contract stays as it is, but the top bar loses the name and the visual baselines must be
    regenerated.
- [ ] **14 decisions to confirm** in `docs/handoff/m0-star-open-questions.md` (#6 is already resolved):
  1. E01-01: acceptance pins mirrored into the root `dev` group; `tests/requirements.txt` kept.
  2. E01-02/03: spec-owned tests and `scripts/backlog_tools.py` excluded from ruff and Prettier (91 findings).
  3. E12-02: ADR-0013 theme thresholds unchanged.
  4. E12-03: root docs MIT, lockfiles and root tooling AGPL (`REUSE.toml`).
  5. E12-03: Contributor Covenant 3.0.
  6. (resolved by ADR 0015)
  7. E10-01/E13-04: the `settings.theme_changed` schema added early, in E10-01.
  8. E13-01: `style` keys allowed only in the two fields the contract defines.
  9. E07-02: a PATCH that sets `done=true` emits only `hauskraft.task.completed`.
  10. E08-06: dashboard layout saves call `authorize()` but emit no event.
  11. E08-04: the navigation landmark stays "Main" in German.
  12. E13-02: `data-hauskraft-button` as in ui-contract; `packages/ui/AGENTS.md` to be aligned.
  13. E06-05: plugin contract additions (`prefetch`, `useHost()`, `toast`).
  14. E09-01: widget tests use a fetch stub instead of MSW.
  15. E06-06: `pnpm gen:plugins` runs through `just gen`.
- [ ] **`unit-web` hits its 8-minute limit when Ubuntu's package mirror is slow.** Its browser setup installs
      fonts through apt. On 2026-10-22 the mirror ran at about 40 KB/s, and GitHub cancelled the job four times
      (#75, #80, #81, #83), each time costing a ~10-minute rerun. The E02 acceptance criterion says these jobs finish in under 8 minutes, so the fix is your call. Options:
      run the job in Playwright's container image, which has the browser and fonts preinstalled, or allow more
      time.
- [ ] **Notes for later** in the same file: eight follow-ups, such as the full TanStack denylist, the 405 `Allow`
      header, a Hackspace heading scale and the devcontainer check. Decide which go into M1.
- [ ] **M1 backlog** (Governed gateway + HA bridge): Claude drafts it, you review it.

## Dependabot (status 2026-10-22, 15:30 UTC)

Merged today: #80 (config: Playwright's packages update together, axe-core on its own), #75 (Python: FastAPI
0.147, Schemathesis 4.32, Ruff 0.17.1), #83 (React 19.3.1, TanStack, i18next, Lucide 1.59, Vitest 4.1.12) and
#82 (`@eslint/css`, `typescript-eslint`). No open Dependabot PRs are left.

- [ ] **Playwright 1.64.1 and axe-core 4.14** come back as two new PRs with Dependabot's next full run, on Monday
      2026-10-26. To get them sooner: Insights → Dependency graph → Dependabot, then "Check for updates" for npm.
  - Playwright (`playwright` and `@playwright/test` together): Claude merges it when green.
  - axe-core 4.14 fails `e2e` until the account menu name is fixed (see above). Its PR stays open until then.

## On Claude's side

- [ ] Remove the `/root/proj/hearthos` symlink and the old `hearthos/*:dev` Docker images once no session uses
      them.
