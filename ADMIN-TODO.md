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

- [x] **Account menu name.** Decided 2026-10-22: the button shows "Account menu", not the user's name. Fixed in
      #84 (one-off permission for the ui-contract note and the visual baselines).
- [ ] **Review and merge PR #85: M1\* Household basics** (spec v0.3, ADRs 0016–0018, backlog of 35 stories, red
      acceptance tests). It's spec-owned, so you merge it. Please also:
  - set ADRs 0016–0018 from *Proposed* to *Accepted* if you agree (decisions D11–D14 from 2026-10-22);
  - confirm the two narrowed M0\* assertions listed in the PR (`demo` becomes owner, `owner` becomes creatable).
  After the merge, Claude creates the Linear project "Hauskraft M1\*" (one issue per story) and fixes the spec link
  in the M0\* project description, which still points at `hauskraft-spec-v0.2.md`.
- [ ] **14 M0\* decisions to confirm:** now Linear NIE-79 (assigned to you), with the list from
      `docs/handoff/m0-star-open-questions.md`.
- [ ] **`unit-web` 8-minute limit** when Ubuntu's package mirror is slow: now Linear NIE-87 (your call: Playwright's
      container image, or more time).
- [x] **Notes for later** from the M0\* hand-off: moved to Linear "Hauskraft Backlog", NIE-80 to NIE-86. Nothing of
      it is in M1\*.
- [x] **Next milestone decided** (2026-10-22): M1\* Household basics instead of "Governed gateway + HA bridge". The
      deferred topics are in Linear "Hauskraft Backlog" (P-NIE-2), NIE-66 to NIE-78.

## Dependabot (status 2026-10-22, 15:30 UTC)

Merged today: #80 (config: Playwright's packages update together, axe-core on its own), #75 (Python: FastAPI
0.147, Schemathesis 4.32, Ruff 0.17.1), #83 (React 19.3.1, TanStack, i18next, Lucide 1.59, Vitest 4.1.12) and
#82 (`@eslint/css`, `typescript-eslint`). No open Dependabot PRs are left.

- [ ] **Playwright 1.64.1 and axe-core 4.14** come back as two new PRs with Dependabot's next full run, on Monday
      2026-10-26. To get them sooner: Insights → Dependency graph → Dependabot, then "Check for updates" for npm.
  - Playwright (`playwright` and `@playwright/test` together): Claude merges it when green.
  - axe-core 4.14: passes with the #84 fix (checked locally). Claude merges it when green.

## On Claude's side

- [ ] Remove the `/root/proj/hearthos` symlink and the old `hearthos/*:dev` Docker images once no session uses
      them.
