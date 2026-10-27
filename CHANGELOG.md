# Changelog

All notable changes to Hauskraft. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
milestones stand in for releases until the first one is published.

## Unreleased

### M2\* Agentic harness (done 2026-10-27)

Members hand work to an assistant that acts with their permissions, safely. Spec v0.4 §8.0; ADRs 0019–0023; backlog
`docs/backlog/m2-star/`.

- **Assistant panel:** the "Assistant" button opens a side panel on every page. Chat to add, find, complete or delete
  tasks; every change shows as a card with Open and Undo; deleting waits for a click. Chats are private and kept
  until deleted.
- **Settings → Assistant (owners):** an OpenAI-compatible Chat Completions endpoint with an encrypted, write-only API
  key and a connection test; tool switches; token usage per day, member and model with an estimated cost.
- **Tools and skills for plugins:** one tool contract (`hauskraft_sdk.tools.ToolSpec`, manifest `contributes.tools`)
  and a registry that offers each run only the tools it may use; `SKILL.md` skills. The tasks plugin offers four
  tools, "Add from text" on All tasks and a "Weekly overview" widget.
- **Safety:** a gate (allow, confirm, deny) with confirmation for destructive tools, Undo for reversible ones, run
  limits, and "via assistant" in Activity (`agentrunid` on events).
- **Evals:** a fake OpenAI-compatible model keeps CI free and deterministic; real-model evals run on demand.
  The first real-model run met every threshold ([evals/README.md](evals/README.md#results)).
- **Docs:** [docs/assistant.md](docs/assistant.md) and [docs/plugins/tools-and-skills.md](docs/plugins/tools-and-skills.md).

### M1\* Household basics (done 2026-10-23)

A real household can install Hauskraft without demo data, set it up in the browser, add its members and manage its
own accounts. Spec v0.3 §2.3; ADRs 0016–0018; backlog `docs/backlog/m1-star/`.

- **First-run setup:** while no account exists, every page leads to "Set up your household", which creates the
  household settings and its first owner in one step (the first visitor wins, ADR 0017). The web port listens on
  `127.0.0.1` by default (`HAUSKRAFT_WEB_BIND`).
- **Owner and adult roles:** a static permission table behind `authorize()` (ADR 0016). Owners manage members,
  household settings, the theme and plugins; both roles share tasks and their own accounts. Sessions carry the
  role's permissions. An upgrade from M0\* makes the oldest active account the owner; the demo seed has `demo` as
  owner and `alex` as adult.
- **Members (Settings → Members):** add with a temporary password, edit name and role, reset a password, deactivate
  and reactivate. There is always at least one active owner. New and reset accounts must choose their own password
  first ("Choose a new password").
- **My account (Settings → Account):** display name, language, password, signed-in devices, sign out everywhere.
- **Household settings (Settings → Household):** name (in the browser title), time zone (decides "today" for due
  dates on every device) and default language for new members.
- **Sign-in:** an ended session explains itself and returns to the page; deactivated accounts get a clear message;
  password rules show before typing; password-manager-friendly `autocomplete`.
- **Account events:** member, password and household changes are CloudEvents with closed schemas (ADR 0018) and show
  in Activity in English and German.
- **CLI:** `hauskraft users list|create|set-password|deactivate|reactivate` for recovery when no owner can sign in.
- **Testing:** a fresh, unseeded stack (`just fresh-up`, port 8081) runs next to the demo stack locally and in CI;
  `tests/e2e/basics.spec.ts` automates the M1\* demo.
- **Docs:** [docs/household-admin.md](docs/household-admin.md) and the M1\* steps in
  [docs/how-to-test.md](docs/how-to-test.md).

### M0\* Scaffolding MVP (done 2026-10-22)

The native Tasks plugin on a themeable Today dashboard, the in-process plugin loader, three built-in themes with
function invariance, CloudEvents with an outbox and Activity, and the one-command Docker Compose demo.
