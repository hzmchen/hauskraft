# Contributing

Thanks for helping. HearthOS is built story by story from the backlog, test-first. This first version covers the essentials; M0S-E12-03 completes it.

## The workflow
1. Pick a story from [docs/backlog/m0-star/](docs/backlog/m0-star/README.md) whose dependencies are merged.
2. Work **red → green → refactor** as described in [AGENTS.md](AGENTS.md) and [docs/testing/README.md](docs/testing/README.md):
   run the story's acceptance tests and see them fail, write your own tests first, implement, refactor, then flip the story to green in `tests/story-status.json`.
3. Open one PR per story, titled `[M0S-Exx-yy] …`, with conventional commits. The red commit comes before the green one.

## Rules that save review time
- Spec-owned tests under `tests/acceptance/`, `tests/e2e/` and `tests/fixtures/` are not changed in story PRs. If one looks wrong, say so in the PR.
- No raw styles in UI code: use `@hearthos/ui` primitives and semantic tokens only (no colour literals, palette classes or arbitrary values).
- User-facing strings exist in English and German.
- New dependencies come with a lockfile update and a reason in the PR.

## Sign-off (DCO)
Sign every commit: `git commit -s`. This certifies the [Developer Certificate of Origin](https://developercertificate.org/). There is no CLA.

## AI-assisted contributions
AI coding agents are welcome and expected. Say in the PR which parts were AI-generated, make sure a human has read the diff, and follow [AGENTS.md](AGENTS.md). The human who signs off is responsible for the contribution.
