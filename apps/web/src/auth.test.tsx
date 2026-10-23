// SPDX-License-Identifier: AGPL-3.0-or-later
import { getCsrfToken, setCsrfToken, usersMeGet } from "@hauskraft/sdk-ts";
import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./app";
import { createI18n } from "./i18n";
import { createAppRouter } from "./router";
import { DEMO_SESSION, fakeApi, json, problem } from "./test/fakeApi";

function start(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createAppRouter({ initialPath: path, queryClient, i18n: createI18n({ lng: "en" }) });
  render(<App router={router} queryClient={queryClient} />);
  return { router, queryClient };
}

beforeEach(() => localStorage.clear());
afterEach(() => {
  vi.unstubAllGlobals();
  setCsrfToken(null);
});

describe("auth guard", () => {
  it("sends a signed-out visitor to /login with the page to return to", async () => {
    fakeApi({ "GET /api/v1/auth/session": () => problem(401, "unauthenticated") });
    const { router } = start("/today");
    await screen.findByRole("button", { name: "Sign in" });
    expect(router.state.location.pathname).toBe("/login");
    expect(router.state.location.search).toEqual({ redirect: "/today" });
  });

  it("lets a signed-in user through and keeps the CSRF token in memory", async () => {
    fakeApi({ "GET /api/v1/auth/session": () => json(DEMO_SESSION) });
    const { router } = start("/today");
    await screen.findByRole("heading", { level: 1, name: "Today" });
    expect(router.state.location.pathname).toBe("/today");
    expect(getCsrfToken()).toBe("csrf-123");
  });
});

describe("login", () => {
  it("shows one message for a wrong password, without naming the field", async () => {
    fakeApi({
      "GET /api/v1/auth/session": () => problem(401, "unauthenticated"),
      "POST /api/v1/auth/login": () => problem(401, "invalid_credentials"),
    });
    start("/login");
    await userEvent.type(await screen.findByRole("textbox", { name: "Username" }), "demo");
    await userEvent.type(screen.getByLabelText("Password"), "nope");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Wrong username or password");
  });

  it("explains a deactivated account, but keeps one message for wrong credentials (M1S-E07-04)", async () => {
    let deactivated = true;
    fakeApi({
      "GET /api/v1/auth/session": () => problem(401, "unauthenticated"),
      "POST /api/v1/auth/login": () =>
        deactivated ? problem(403, "account_deactivated") : problem(401, "invalid_credentials"),
    });
    start("/login");
    const username = await screen.findByRole("textbox", { name: "Username" });
    expect(username.getAttribute("autocomplete")).toBe("username");
    expect(screen.getByLabelText("Password").getAttribute("autocomplete")).toBe("current-password");
    await userEvent.type(username, "gone");
    await userEvent.type(screen.getByLabelText("Password"), "correct-horse-battery");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect((await screen.findByRole("alert")).textContent).toBe(
      "This account is deactivated. Ask an owner of your household.",
    );
    deactivated = false;
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("Wrong username or password"));
  });

  it("signs in and goes to the requested page", async () => {
    let signedIn = false;
    const calls = fakeApi({
      "GET /api/v1/auth/session": () => (signedIn ? json(DEMO_SESSION) : problem(401, "unauthenticated")),
      "POST /api/v1/auth/login": () => {
        signedIn = true;
        return json(DEMO_SESSION);
      },
    });
    const { router } = start("/login?redirect=%2Ftoday");
    await userEvent.type(await screen.findByRole("textbox", { name: "Username" }), "demo");
    await userEvent.type(screen.getByLabelText("Password"), "hauskraft-demo");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await screen.findByRole("heading", { level: 1, name: "Today" });
    expect(router.state.location.pathname).toBe("/today");
    const login = calls.find((r) => r.url.endsWith("/auth/login"))!;
    expect(await login.clone().json()).toEqual({ username: "demo", password: "hauskraft-demo" });
  });

  it("never redirects off-site after sign-in", async () => {
    fakeApi({
      "GET /api/v1/auth/session": () => problem(401, "unauthenticated"),
      "POST /api/v1/auth/login": () => json(DEMO_SESSION),
    });
    const { router } = start("/login?redirect=%2F%2Fevil.example");
    await userEvent.type(await screen.findByRole("textbox", { name: "Username" }), "demo");
    await userEvent.type(screen.getByLabelText("Password"), "x");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/today"));
  });
});

describe("sign out", () => {
  it("ends the session, clears cached data and returns to /login", async () => {
    let signedIn = true;
    const calls = fakeApi({
      "GET /api/v1/auth/session": () => (signedIn ? json(DEMO_SESSION) : problem(401, "unauthenticated")),
      "POST /api/v1/auth/logout": () => {
        signedIn = false;
        return new Response(null, { status: 204 });
      },
    });
    const { router, queryClient } = start("/today");
    queryClient.setQueryData(["private"], "household data");
    await userEvent.click(await screen.findByRole("button", { name: "Account menu" }));
    await userEvent.click(await screen.findByRole("menuitem", { name: "Sign out" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
    expect(queryClient.getQueryData(["private"])).toBeUndefined();
    expect(getCsrfToken()).toBeNull();
    expect(calls.find((r) => r.url.endsWith("/auth/logout"))!.headers.get("X-CSRF-Token")).toBe("csrf-123");
  });
});

describe("ended session (M1S-E07-03)", () => {
  const ENDED = "Your session has ended. Please sign in again.";

  function household(state: { signedIn: boolean }) {
    return fakeApi({
      "GET /api/v1/auth/session": () => (state.signedIn ? json(DEMO_SESSION) : problem(401, "unauthenticated")),
      "GET /api/v1/me": () => (state.signedIn ? json(DEMO_SESSION.user) : problem(401, "unauthenticated")),
      "POST /api/v1/auth/login": () => {
        state.signedIn = true;
        return json(DEMO_SESSION);
      },
    });
  }

  it("a 401 while signed in goes to sign-in, says why, and returns to the page afterwards", async () => {
    const state = { signedIn: true };
    household(state);
    const { router, queryClient } = start("/activity?page=2");
    await screen.findByRole("heading", { level: 1, name: "Activity" });
    queryClient.setQueryData(["private"], "household data");
    state.signedIn = false; // signed out everywhere from another device
    await usersMeGet();
    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
    expect(router.state.location.search).toEqual({ redirect: "/activity?page=2", reason: "expired" });
    expect((await screen.findByRole("status")).textContent).toBe(ENDED);
    expect(queryClient.getQueryData(["private"])).toBeUndefined();
    expect(getCsrfToken()).toBeNull();

    await userEvent.type(screen.getByRole("textbox", { name: "Username" }), "demo");
    await userEvent.type(screen.getByLabelText("Password"), "hauskraft-demo");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/activity"));
    expect(router.state.location.searchStr).toBe("?page=2");
  });

  it("a wrong password on the sign-in page is not an ended session", async () => {
    fakeApi({
      "GET /api/v1/auth/session": () => problem(401, "unauthenticated"),
      "POST /api/v1/auth/login": () => problem(401, "invalid_credentials"),
    });
    const { router } = start("/login");
    await userEvent.type(await screen.findByRole("textbox", { name: "Username" }), "demo");
    await userEvent.type(screen.getByLabelText("Password"), "nope");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await screen.findByRole("alert");
    expect(screen.queryByRole("status")).toBeNull();
    expect(router.state.location.search).toEqual({});
  });

  it("signing out on purpose shows no message", async () => {
    const state = { signedIn: true };
    fakeApi({
      "GET /api/v1/auth/session": () => (state.signedIn ? json(DEMO_SESSION) : problem(401, "unauthenticated")),
      "POST /api/v1/auth/logout": () => {
        state.signedIn = false;
        return new Response(null, { status: 204 });
      },
    });
    const { router } = start("/today");
    await userEvent.click(await screen.findByRole("button", { name: "Account menu" }));
    await userEvent.click(await screen.findByRole("menuitem", { name: "Sign out" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
    await screen.findByRole("button", { name: "Sign in" });
    expect(screen.queryByText(ENDED)).toBeNull();
  });

  it("the message is in German too", async () => {
    fakeApi({ "GET /api/v1/auth/session": () => problem(401, "unauthenticated") });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const router = createAppRouter({
      initialPath: "/login?reason=expired",
      queryClient,
      i18n: createI18n({ lng: "de" }),
    });
    render(<App router={router} queryClient={queryClient} />);
    expect((await screen.findByRole("status")).textContent).toBe(
      "Deine Sitzung ist abgelaufen. Bitte melde dich erneut an.",
    );
  });
});

describe("language (M1S-E05-03)", () => {
  it("applies the account's language on load when this device chose none", async () => {
    fakeApi({
      "GET /api/v1/auth/session": () => json({ ...DEMO_SESSION, user: { ...DEMO_SESSION.user, locale: "de" } }),
      "GET /api/v1/themes": () => json([]),
    });
    start("/today");
    expect(await screen.findByRole("heading", { level: 1, name: "Heute" })).toBeDefined();
  });

  it("keeps this device's own choice", async () => {
    localStorage.setItem("hauskraft.locale", "en");
    fakeApi({
      "GET /api/v1/auth/session": () => json({ ...DEMO_SESSION, user: { ...DEMO_SESSION.user, locale: "de" } }),
      "GET /api/v1/themes": () => json([]),
    });
    start("/today");
    expect(await screen.findByRole("heading", { level: 1, name: "Today" })).toBeDefined();
  });
});

describe("account menu", () => {
  it("opens account settings from 'Account settings', above 'Sign out' (M1S-E08-03)", async () => {
    fakeApi({ "GET /api/v1/auth/session": () => json(DEMO_SESSION), "GET /api/v1/themes": () => json([]) });
    const { router } = start("/today");
    await userEvent.click(await screen.findByRole("button", { name: "Account menu" }));
    const items = (await screen.findAllByRole("menuitem")).map((i) => i.textContent);
    expect(items.indexOf("Account settings")).toBeGreaterThanOrEqual(0);
    expect(items.indexOf("Account settings")).toBeLessThan(items.indexOf("Sign out"));
    await userEvent.click(screen.getByRole("menuitem", { name: "Account settings" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/settings/account"));
  });

  it("shows its accessible name as its label, not the user's name (WCAG 2.5.3, label in name)", async () => {
    fakeApi({ "GET /api/v1/auth/session": () => json(DEMO_SESSION) });
    start("/today");
    const button = await screen.findByRole("button", { name: "Account menu" });
    expect(button.textContent).toBe("Account menu");
  });
});
