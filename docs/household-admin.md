<!-- SPDX-License-Identifier: MIT -->

# Running your household

This page is for whoever installs Hauskraft and looks after the household's accounts: setting it up, adding the family,
helping someone who forgot their password, and getting back in if nobody can sign in. It covers M1\* ("Household
basics"). The background is in [spec §2.3](spec/hauskraft-spec-v0.4.md) and ADRs
[0016](adr/0016-static-role-permissions.md), [0017](adr/0017-first-run-setup.md) and
[0018](adr/0018-account-events.md).

## Install for real

```bash
git clone https://github.com/hzmchen/hauskraft.git
cd hauskraft
HAUSKRAFT_SEED_DEMO=false docker compose up --wait
```

Then open <http://localhost:8080> on the same machine and finish the setup straight away (see below). Without
`HAUSKRAFT_SEED_DEMO=false` you get the demo household with the public demo password instead; that is for trying
Hauskraft, not for living with it.

For a lasting install, copy [`deploy/compose/.env.example`](../deploy/compose/.env.example) to `.env` in the repository
root and set at least `HAUSKRAFT_ENV=production` and a random `HAUSKRAFT_SECRET_KEY` (at least 32 characters, for
example `python -c "import secrets; print(secrets.token_urlsafe(48))"`). Your data lives in the Compose volume
`hauskraft_hauskraft_pg`; `docker compose down` keeps it, `docker compose down -v` deletes it.

## The setup wizard and the first-visitor rule

While the household has no account, every page leads to **Set up your household**. It asks for the household's name,
language and time zone, and for your name, username and password (at least 12 characters). Whoever completes it first
becomes the household's first **owner**; afterwards the wizard is closed for good and everyone signs in normally.

Because the first visitor wins, nobody else should be able to reach a fresh install before you have set it up. That is
why the web port listens on this machine only by default (`HAUSKRAFT_WEB_BIND=127.0.0.1`). Finish the setup from the
same machine, then open it to your network if you want to (next section).

## Opening Hauskraft to your network

`HAUSKRAFT_WEB_BIND` is the address the web port listens on. `127.0.0.1` (the default) means this machine only;
`0.0.0.0` means every network interface, so phones and laptops in your home network can reach it.

Only open it up behind **TLS**: without HTTPS, passwords and session cookies cross the network in clear text. Put a
reverse proxy with a certificate in front of the web port (Caddy, Traefik, nginx or your router's proxy), then set
`HAUSKRAFT_COOKIE_SECURE=true` and `HAUSKRAFT_ALLOWED_ORIGINS` to the address people open (for example
`https://hauskraft.home.example`). Sign-in from any other origin is refused.

## Roles

| | Owner | Adult |
|---|---|---|
| Tasks, own Today layout, own account (name, language, password, devices) | yes | yes |
| This device's colour mode | yes | yes |
| Household settings (name, time zone, default language) | yes | — |
| The household theme | yes | — |
| Turning plugins on and off | yes | — |
| Members: add, edit, deactivate, reactivate, reset passwords | yes | — |

There is always at least one active owner: Hauskraft refuses to demote or deactivate the last one (including
yourself) with "The household needs at least one active owner." To step down, first make someone else an owner. Other
roles (teen, kid, guest and so on) come in later milestones.

## Members

Owners manage everyone in **Settings → Members**:

- **Add member:** display name, username, role (Owner or Adult) and a **temporary password**. Tell the person their
  temporary password in person. When they sign in for the first time, they must choose their own password before they
  can do anything else. New members start in the household's default language and can change it in their account.
- **Edit:** display name and role. Usernames can't be changed.
- **Reset password:** for someone who forgot theirs. You set a new temporary password, all their sessions end, and
  they choose their own at the next sign-in. Your own password you change in **Settings → Account**.
- **Deactivate:** for someone who moved out or a lost account. They are signed out everywhere and can't sign in
  (sign-in says "This account is deactivated. Ask an owner of your household."). Nothing is deleted: their tasks and
  Activity entries keep their name. **Reactivate** lets them sign in again with their old password.

Every one of these changes, and every password change, appears in **Activity**, so the household sees who changed
which account.

## Household settings

**Settings → Household** (owners) holds the household's name, which appears in the browser title, its **time zone**,
which decides what "today" means for due dates on every device, and the default language for new members.

## Your own account

**Settings → Account** (everyone): display name and language, password (you need the current one), and the devices you
are signed in on. Sign out a device you don't recognise, or **Sign out everywhere** if a phone is lost.

## If nobody can sign in

The command line inside the `api` container can do what owners do in the app. It acts as the system and needs no
account, so it is the way back in when every owner has forgotten their password:

```bash
docker compose exec api hauskraft users list                       # every account with role and status
docker compose exec api hauskraft users set-password mia           # prompts for a new password
docker compose exec api hauskraft users set-password alex --temporary   # they choose their own at sign-in
docker compose exec api hauskraft users create --username jonas --role owner --temporary
docker compose exec api hauskraft users deactivate alex
docker compose exec api hauskraft users reactivate alex
```

`hauskraft users list --json` prints the same list as JSON. The CLI keeps the last-owner rule, ends sessions where the
app would, and writes the same Activity entries.
