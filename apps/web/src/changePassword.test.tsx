// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./app";
import { createI18n } from "./i18n";
import { createAppRouter } from "./router";
import { DEMO_SESSION, fakeApi, json, problem } from "./test/fakeApi";

const LOCKED = { ...DEMO_SESSION, user: { ...DEMO_SESSION.user, must_change_password: true } };

function start(path: string, lng: "en" | "de" = "en") {
  const state = { locked: true, signedIn: true, body: null as unknown };
  fakeApi({
    "GET /api/v1/auth/session": () =>
      state.signedIn ? json(state.locked ? LOCKED : DEMO_SESSION) : problem(401, "unauthenticated"),
    "POST /api/v1/auth/login": () => {
      state.signedIn = true;
      return json(LOCKED);
    },
    "POST /api/v1/me/password": async (request) => {
      state.body = await request.json();
      state.locked = false;
      return new Response(null, { status: 204 });
    },
    "GET /api/v1/themes": () => json([]),
    "GET /api/v1/activity": () => json([]),
  });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createAppRouter({ initialPath: path, queryClient, i18n: createI18n({ lng }) });
  render(<App router={router} queryClient={queryClient} />);
  return { router, state };
}

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

describe("choose a new password (M1S-E07-02)", () => {
  it("sends a locked account from any app route to /change-password, remembering the target", async () => {
    const { router } = start("/activity");
    expect(await screen.findByRole("heading", { level: 1, name: "Choose a new password" })).toBeDefined();
    expect(router.state.location.pathname).toBe("/change-password");
    expect(router.state.location.search).toEqual({ redirect: "/activity" });
    expect(screen.getByText("Your password was set by someone else. Choose your own to continue.")).toBeDefined();
    expect(screen.getByText("At least 12 characters")).toBeDefined();
    expect(screen.queryByRole("navigation", { name: "Main" })).toBeNull();
  });

  it("saves the new password and continues to the target", async () => {
    const { router, state } = start("/change-password?redirect=%2Factivity");
    await userEvent.type(await screen.findByLabelText("Current password", { exact: true }), "temporary-pass-1234");
    await userEvent.type(screen.getByLabelText("New password", { exact: true }), "member-chosen-pass-5678");
    await userEvent.type(screen.getByLabelText("Repeat new password", { exact: true }), "member-chosen-pass-5678");
    expect(screen.getByLabelText("New password", { exact: true }).getAttribute("autocomplete")).toBe("new-password");
    await userEvent.click(screen.getByRole("button", { name: "Save password" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/activity"));
    expect(state.body).toEqual({ current_password: "temporary-pass-1234", new_password: "member-chosen-pass-5678" });
  });

  it("goes there straight after signing in with a temporary password", async () => {
    const { router, state } = start("/login?redirect=%2Fp%2Ftasks");
    state.signedIn = false;
    await userEvent.type(await screen.findByRole("textbox", { name: "Username" }), "anna");
    await userEvent.type(screen.getByLabelText("Password"), "temporary-pass-1234");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/change-password"));
    expect(router.state.location.search).toEqual({ redirect: "/p/tasks" });
  });

  it("speaks German for a German household", async () => {
    start("/change-password", "de");
    expect(await screen.findByRole("heading", { level: 1, name: "Neues Passwort wählen" })).toBeDefined();
    expect(screen.getByLabelText("Aktuelles Passwort", { exact: true })).toBeDefined();
    expect(screen.getByLabelText("Neues Passwort", { exact: true })).toBeDefined();
    expect(screen.getByLabelText("Neues Passwort wiederholen", { exact: true })).toBeDefined();
    expect(screen.getByRole("button", { name: "Passwort speichern" })).toBeDefined();
  });

  it("checks that both new passwords match", async () => {
    start("/change-password");
    await userEvent.type(await screen.findByLabelText("Current password", { exact: true }), "temporary-pass-1234");
    await userEvent.type(screen.getByLabelText("New password", { exact: true }), "member-chosen-pass-5678");
    await userEvent.type(screen.getByLabelText("Repeat new password", { exact: true }), "something-else-5678");
    await userEvent.click(screen.getByRole("button", { name: "Save password" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Passwords do not match");
  });
});
