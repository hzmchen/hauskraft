# Changelog

All notable changes to Hauskraft. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
milestones stand in for releases until the first one is published.

## Unreleased

### M1\* Household basics

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
