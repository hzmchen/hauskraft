// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../app";
import { createI18n } from "../i18n";
import { createAppRouter } from "../router";
import { OWNER_SESSION, fakeApi, json, problem } from "../test/fakeApi";

const member = (id: string, username: string, display_name: string, role: string, is_active = true) => ({
  id,
  username,
  display_name,
  role,
  locale: "en",
  must_change_password: false,
  is_active,
  created_at: "2026-10-01T08:00:00Z",
  last_login_at: null,
});
const ME = member(OWNER_SESSION.user.id, "demo", "Demo Adult", "owner");
const ALEX = member("0199f391-3333-7aaa-8bbb-dddddddddddd", "alex", "Alex Adult", "adult");
const GONE = member("0199f391-3333-7aaa-8bbb-eeeeeeeeeeee", "gone", "Gone Member", "adult", false);
const LAST_OWNER = "The household needs at least one active owner.";

type Routes = Parameters<typeof fakeApi>[0];

function start(extra: Routes = {}) {
  let members = [ME, ALEX, GONE];
  const sent: { method: string; path: string; body: unknown }[] = [];
  const record = (answer: (body: Record<string, unknown>, path: string) => Response) => async (request: Request) => {
    const body = (await request.json().catch(() => null)) as Record<string, unknown>;
    const path = new URL(request.url).pathname.replace("/api/v1", "");
    sent.push({ method: request.method, path, body });
    return answer(body, path);
  };
  const update = (id: string, change: Record<string, unknown>) => {
    members = members.map((m) => (m.id === id ? { ...m, ...change } : m));
    return json(members.find((m) => m.id === id));
  };
  fakeApi({
    "GET /api/v1/auth/session": () => json(OWNER_SESSION),
    "GET /api/v1/themes": () => json([]),
    "GET /api/v1/users": () => json(members),
    "POST /api/v1/users": record((body) => {
      const created = member(
        "0199f391-3333-7aaa-8bbb-ffffffffffff",
        String(body.username),
        String(body.display_name),
        String(body.role ?? "adult"),
      );
      members = [...members, created];
      return json({ ...created, must_change_password: true }, 201);
    }),
    [`PATCH /api/v1/users/${ALEX.id}`]: record((body) => update(ALEX.id, body)),
    [`POST /api/v1/users/${ALEX.id}/password`]: record(() => new Response(null, { status: 204 })),
    [`POST /api/v1/users/${ALEX.id}/deactivate`]: record(() => update(ALEX.id, { is_active: false })),
    [`POST /api/v1/users/${GONE.id}/reactivate`]: record(() => update(GONE.id, { is_active: true })),
    ...extra,
  });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createAppRouter({ initialPath: "/settings/members", queryClient, i18n: createI18n({ lng: "en" }) });
  render(<App router={router} queryClient={queryClient} />);
  return sent;
}

const rows = async () => within(await screen.findByRole("list", { name: "Members" })).findAllByRole("listitem");
const row = async (username: string) => (await rows()).find((li) => li.textContent?.includes(username))!;

afterEach(() => vi.unstubAllGlobals());

describe("Settings → Members (M1S-E06-05)", () => {
  it("lists every member with role and status and the right actions", async () => {
    start();
    expect(await screen.findByRole("heading", { level: 1, name: "Members" })).toBeDefined();
    await waitFor(async () => expect(await rows()).toHaveLength(3));
    expect((await row("demo")).textContent).toContain("Owner");
    expect((await row("alex")).textContent).toContain("Adult");
    expect((await row("gone")).textContent).toContain("Deactivated");
    expect(screen.getByRole("button", { name: "Edit Alex Adult" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Reset password for Alex Adult" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Deactivate Alex Adult" })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Reset password for Demo Adult" })).toBeNull();
    expect(screen.getByRole("button", { name: "Reactivate Gone Member" })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Deactivate Gone Member" })).toBeNull();
  });

  it("adds a member with a temporary password", async () => {
    const sent = start();
    await userEvent.click(await screen.findByRole("button", { name: "Add member" }));
    const dialog = await screen.findByRole("dialog", { name: "Add member" });
    expect(dialog.textContent).toContain("At least 12 characters");
    const password = within(dialog).getByLabelText("Temporary password", { exact: true });
    expect(password.getAttribute("autocomplete")).toBe("new-password");
    expect((within(dialog).getByRole("combobox", { name: "Role" }) as HTMLSelectElement).value).toBe("adult");
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Display name" }), "Jonas");
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Username" }), "jonas");
    await userEvent.selectOptions(within(dialog).getByRole("combobox", { name: "Role" }), "Owner");
    await userEvent.type(password, "temporary-pass-1234");
    await userEvent.click(within(dialog).getByRole("button", { name: "Add member" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Add member" })).toBeNull());
    expect(sent.find((s) => s.method === "POST" && s.path === "/users")?.body).toEqual({
      display_name: "Jonas",
      username: "jonas",
      role: "owner",
      password: "temporary-pass-1234",
    });
    expect((await row("jonas")).textContent).toContain("Owner");
  });

  it("shows a taken username next to the field", async () => {
    start({ "POST /api/v1/users": () => problem(409, "username_taken") });
    await userEvent.click(await screen.findByRole("button", { name: "Add member" }));
    const dialog = await screen.findByRole("dialog", { name: "Add member" });
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Display name" }), "Alex Again");
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Username" }), "alex");
    await userEvent.type(within(dialog).getByLabelText("Temporary password", { exact: true }), "temporary-pass-1234");
    await userEvent.click(within(dialog).getByRole("button", { name: "Add member" }));
    expect((await within(dialog).findByRole("alert")).textContent).toBe("This username is already taken.");
  });

  it("edits a member and shows the last-owner rule", async () => {
    const sent = start({ [`PATCH /api/v1/users/${ME.id}`]: () => problem(409, "last_owner") });
    await userEvent.click(await screen.findByRole("button", { name: "Edit Alex Adult" }));
    let dialog = await screen.findByRole("dialog", { name: "Edit member" });
    const name = within(dialog).getByRole("textbox", { name: "Display name" });
    await userEvent.clear(name);
    await userEvent.type(name, "Alex M.");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Edit member" })).toBeNull());
    expect(sent.find((s) => s.method === "PATCH")?.body).toEqual({ display_name: "Alex M.", role: "adult" });
    expect(await screen.findByRole("button", { name: "Edit Alex M." })).toBeDefined();

    await userEvent.click(screen.getByRole("button", { name: "Edit Demo Adult" }));
    dialog = await screen.findByRole("dialog", { name: "Edit member" });
    await userEvent.selectOptions(within(dialog).getByRole("combobox", { name: "Role" }), "Adult");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect((await within(dialog).findByRole("alert")).textContent).toBe(LAST_OWNER);
  });

  it("resets a password with a temporary one", async () => {
    const sent = start();
    await userEvent.click(await screen.findByRole("button", { name: "Reset password for Alex Adult" }));
    const dialog = await screen.findByRole("dialog", { name: "Reset password?" });
    expect(dialog.textContent).toContain("At least 12 characters");
    await userEvent.type(
      within(dialog).getByLabelText("Temporary password", { exact: true }),
      "reset-temporary-pass-42",
    );
    await userEvent.click(within(dialog).getByRole("button", { name: "Reset password" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Reset password?" })).toBeNull());
    expect(sent.find((s) => s.path.endsWith("/password"))?.body).toEqual({ password: "reset-temporary-pass-42" });
  });

  it("deactivates after confirming and reactivates in one click", async () => {
    start();
    await userEvent.click(await screen.findByRole("button", { name: "Deactivate Alex Adult" }));
    let confirm = await screen.findByRole("alertdialog", { name: "Deactivate Alex Adult?" });
    expect(confirm.textContent).toContain("They are signed out everywhere and can't sign in until reactivated.");
    await userEvent.click(within(confirm).getByRole("button", { name: "Cancel" }));
    expect((await row("alex")).textContent).not.toContain("Deactivated");
    await userEvent.click(screen.getByRole("button", { name: "Deactivate Alex Adult" }));
    confirm = await screen.findByRole("alertdialog", { name: "Deactivate Alex Adult?" });
    await userEvent.click(within(confirm).getByRole("button", { name: "Deactivate" }));
    await waitFor(async () => expect((await row("alex")).textContent).toContain("Deactivated"));
    await userEvent.click(screen.getByRole("button", { name: "Reactivate Gone Member" }));
    await waitFor(async () => expect((await row("gone")).textContent).not.toContain("Deactivated"));
  });

  it("explains why the last owner can't be deactivated", async () => {
    start({ [`POST /api/v1/users/${ME.id}/deactivate`]: () => problem(409, "last_owner") });
    await userEvent.click(await screen.findByRole("button", { name: "Deactivate Demo Adult" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Deactivate Demo Adult?" });
    await userEvent.click(within(confirm).getByRole("button", { name: "Deactivate" }));
    expect((await screen.findByRole("alert")).textContent).toBe(LAST_OWNER);
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });
});
