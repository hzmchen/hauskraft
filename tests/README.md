# HearthOS acceptance suite

Spec-owned tests written before the code. Start with [docs/testing/README.md](../docs/testing/README.md).

```sh
python -m pip install -r tests/requirements.txt
python -m pytest tests                      # meta tests green, story tests red (xfail) until built
python -m pytest tests --story M0S-E07-03   # one story, raw mode: see the real failures
python -m pytest tests --live               # also run live API tests against a running stack
```

| Path | What |
|---|---|
| `conftest.py` | Story markers, red → xfail mapping, `--story`, `--raw`, `--live`, `--strict-status` |
| `story-status.json` | Red/green switch and acceptance kind per story |
| `_support/` | Helpers: colour maths, theme contract, token reader, HTTP client, CLI and tool runners |
| `meta/` | Validation of the docs and of the suite itself (always green) |
| `acceptance/` | Story acceptance tests: `repo`, `schemas`, `themes`, `web`, `api` (live) |
| `fixtures/` | Contract fixtures; see [fixtures/README.md](fixtures/README.md) |
| `e2e/` | Playwright: demo script, tasks UI, theme invariance |
