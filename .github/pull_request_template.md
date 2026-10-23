<!-- Title: [M1S-Exx-yy] Short description. One story per PR; in M1*, one wave per PR: [M1* wave N] …, one block per story. -->

Story: **M0S-Exx-yy** · <title> (<link to the epic file>)

## Acceptance criteria

<!-- Copy the story's AC and tick each one. -->

- [ ] …

## What changed

## Dependencies added

<!-- Package, version, why. Lockfile updated (AGENTS.md rule 8). Write "none" if none. -->

## Tests run

- [ ] Red: `python -m pytest tests --story M0S-Exx-yy` failed for the right reason before the code (red commit comes first)
- [ ] Green: story tests, my unit/integration tests and `python -m pytest tests --strict-status` pass
- [ ] Story flipped to `green` in `tests/story-status.json`; `python scripts/backlog_tools.py coverage --write` and `check` run
- [ ] No file under `tests/acceptance/`, `tests/e2e/` or `tests/fixtures/` was changed to get to green

## UI changes only

- [ ] Screenshots in Default, Paper and Hackspace, light and dark
- [ ] Only `@hauskraft/ui` primitives and semantic tokens (no raw styles)

## Sign-off

- [ ] Every commit is signed off (`git commit -s`, DCO)
- [ ] AI-assisted parts are disclosed below and a human has read the diff
