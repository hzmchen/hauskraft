// SPDX-License-Identifier: AGPL-3.0-or-later
import { getCsrfToken, setCsrfToken } from "@hauskraft/sdk-ts";
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
