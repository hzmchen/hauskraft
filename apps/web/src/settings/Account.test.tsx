// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../app";
import { createI18n } from "../i18n";
import { createAppRouter } from "../router";
import { DEMO_SESSION, fakeApi, json, problem } from "../test/fakeApi";

const sent: { path: string; body: unknown }[] = [];

function start(routes: Record<string, (r: Request) => Response | Promise<Response>> = {}) {
  sent.length = 0;
  const record = (path: string, answer: (body: unknown) => Response) => async (request: Request) => {
    const body = await request.json().catch(() => null);
    sent.push({ path, body });
    return answer(body);
  };
  const calls = fakeApi({
    "GET /api/v1/auth/session": () => json(DEMO_SESSION),
    "GET /api/v1/themes": () => json([]),
    "GET /api/v1/me/sessions": () => json([]),
    "PATCH /api/v1/me": record("/me", (body) => json({ ...DEMO_SESSION.user, ...(body as object) })),
    "POST /api/v1/me/password": record("/me/password", () => new Response(null, { status: 204 })),
    ...routes,
  });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createAppRouter({ initialPath: "/settings/account", queryClient, i18n: createI18n({ lng: "en" }) });
  render(<App router={router} queryClient={queryClient} />);
  return { calls, router };
}

const field = (region: HTMLElement, name: string) => within(region).getByLabelText(name, { exact: true });

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

describe("Settings → Account: profile (M1S-E05-03)", () => {
  it("shows the username read-only and saves name and language", async () => {
    start();
    const profile = await screen.findByRole("region", { name: "Profile" });
    expect(profile.textContent).toContain("demo");
    expect(within(profile).queryByRole("textbox", { name: "Username" })).toBeNull();
    const name = within(profile).getByRole("textbox", { name: "Display name" });
    expect((name as HTMLInputElement).value).toBe("Demo Adult");
    await userEvent.clear(name);
    await userEvent.type(name, "Demo Renamed");
    await userEvent.selectOptions(within(profile).getByRole("combobox", { name: "Language" }), "Deutsch");
    await userEvent.click(within(profile).getByRole("button", { name: "Save profile" }));
    expect(await screen.findByText("Profil gespeichert")).toBeDefined();
    expect(sent.find((s) => s.path === "/me")?.body).toEqual({ display_name: "Demo Renamed", locale: "de" });
    expect(await screen.findByRole("heading", { level: 1, name: "Konto" })).toBeDefined();
  });
});

describe("Settings → Account: password (M1S-E05-03)", () => {
  async function fill(current: string, next: string, repeat: string) {
    const pw = await screen.findByRole("region", { name: "Password" });
    expect(pw.textContent).toContain("At least 12 characters");
    expect(field(pw, "Current password").getAttribute("autocomplete")).toBe("current-password");
    expect(field(pw, "New password").getAttribute("autocomplete")).toBe("new-password");
    expect(field(pw, "Repeat new password").getAttribute("autocomplete")).toBe("new-password");
    for (const [label, value] of [
      ["Current password", current],
      ["New password", next],
      ["Repeat new password", repeat],
    ] as const) {
      await userEvent.clear(field(pw, label));
      await userEvent.type(field(pw, label), value);
    }
    await userEvent.click(within(pw).getByRole("button", { name: "Change password" }));
    return pw;
  }

  it("catches a mismatch without asking the server", async () => {
    start();
    await fill("hauskraft-demo", "brand-new-password-1", "brand-new-password-2");
    expect((await screen.findByRole("alert")).textContent).toBe("Passwords do not match");
    expect(sent.filter((s) => s.path === "/me/password")).toHaveLength(0);
  });

  it("says when the current password is wrong", async () => {
    start({ "POST /api/v1/me/password": () => problem(422, "wrong_password") });
    await fill("not-the-current-one", "brand-new-password-1", "brand-new-password-1");
    expect((await screen.findByRole("alert")).textContent).toBe("The current password is wrong.");
    expect(screen.queryByText("Password changed")).toBeNull();
  });

  it("changes the password and clears the form", async () => {
    start();
    const pw = await fill("hauskraft-demo", "brand-new-password-1", "brand-new-password-1");
    expect(await screen.findByText("Password changed")).toBeDefined();
    expect(sent.find((s) => s.path === "/me/password")?.body).toEqual({
      current_password: "hauskraft-demo",
      new_password: "brand-new-password-1",
    });
    await waitFor(() => expect((field(pw, "New password") as HTMLInputElement).value).toBe(""));
  });
});

describe("Settings → Account: devices (M1S-E05-04)", () => {
  const SESSIONS = [
    {
      id: "0199f390-aaaa-7aaa-8bbb-000000000001",
      device: "Firefox on Linux",
      created_at: "2026-10-20T08:00:00Z",
      last_seen_at: "2026-10-23T09:00:00Z",
      current: true,
    },
    {
      id: "0199f390-aaaa-7aaa-8bbb-000000000002",
      device: "Safari on iPhone",
      created_at: "2026-10-19T08:00:00Z",
      last_seen_at: "2026-10-22T18:00:00Z",
      current: false,
    },
  ];

  it("lists my sessions, marks this device and signs out another one", async () => {
    let sessions = [...SESSIONS];
    const deleted: string[] = [];
    start({
      "GET /api/v1/me/sessions": () => json(sessions),
      [`DELETE /api/v1/me/sessions/${SESSIONS[1]!.id}`]: () => {
        deleted.push(SESSIONS[1]!.id);
        sessions = sessions.filter((s) => s.id !== SESSIONS[1]!.id);
        return new Response(null, { status: 204 });
      },
    });
    const list = await screen.findByRole("list", { name: "Signed-in devices" });
    await waitFor(() => expect(within(list).getAllByRole("listitem")).toHaveLength(2));
    const [current, other] = within(list).getAllByRole("listitem");
    expect(current!.textContent).toContain("Firefox on Linux");
    expect(current!.textContent).toContain("This device");
    expect(within(current!).queryByRole("button", { name: "Sign out" })).toBeNull();
    expect(other!.textContent).toContain("Safari on iPhone");
    await userEvent.click(within(other!).getByRole("button", { name: "Sign out" }));
    await waitFor(() => expect(within(list).getAllByRole("listitem")).toHaveLength(1));
    expect(deleted).toEqual([SESSIONS[1]!.id]);
  });

  it("signs out everywhere after confirming, and returns to sign-in without a session message", async () => {
    let signedIn = true;
    const { router } = start({
      "GET /api/v1/auth/session": () => (signedIn ? json(DEMO_SESSION) : problem(401, "unauthenticated")),
      "GET /api/v1/me/sessions": () => (signedIn ? json(SESSIONS) : problem(401, "unauthenticated")),
      "POST /api/v1/auth/logout-everywhere": () => {
        signedIn = false;
        return new Response(null, { status: 204 });
      },
    });
    await userEvent.click(await screen.findByRole("button", { name: "Sign out everywhere" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Sign out everywhere?" });
    await userEvent.click(within(confirm).getByRole("button", { name: "Sign out everywhere" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
    await screen.findByRole("button", { name: "Sign in" });
    expect(screen.queryByText("Your session has ended. Please sign in again.")).toBeNull();
  });

  it("can cancel signing out everywhere", async () => {
    const calls = start({ "GET /api/v1/me/sessions": () => json(SESSIONS) }).calls;
    await userEvent.click(await screen.findByRole("button", { name: "Sign out everywhere" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Sign out everywhere?" });
    await userEvent.click(within(confirm).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(calls.some((r) => r.url.endsWith("/auth/logout-everywhere"))).toBe(false);
  });
});
