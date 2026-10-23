// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../app";
import { createI18n } from "../i18n";
import { createAppRouter } from "../router";
import { DEMO_SESSION, fakeApi, json, problem } from "../test/fakeApi";

afterEach(() => {
  vi.unstubAllGlobals();
  document.title = "Hauskraft";
});

describe("browser title (M1S-E04-04)", () => {
  it("names the page and the household, and only the app once signed out", async () => {
    let signedIn = true;
    fakeApi({
      "GET /api/v1/auth/session": () => (signedIn ? json(DEMO_SESSION) : problem(401, "unauthenticated")),
      "GET /api/v1/household": () => json({ name: "Familie Müller", timezone: "Europe/Berlin", locale: "en" }),
      "GET /api/v1/themes": () => json([]),
      "POST /api/v1/auth/logout": () => {
        signedIn = false;
        return new Response(null, { status: 204 });
      },
    });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const router = createAppRouter({ initialPath: "/today", queryClient, i18n: createI18n({ lng: "en" }) });
    render(<App router={router} queryClient={queryClient} />);
    await waitFor(() => expect(document.title).toBe("Today · Familie Müller"));
    await router.navigate({ to: "/settings/appearance" });
    await waitFor(() => expect(document.title).toBe("Appearance · Familie Müller"));
    await userEvent.click(await screen.findByRole("button", { name: "Account menu" }));
    await userEvent.click(await screen.findByRole("menuitem", { name: "Sign out" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
    await waitFor(() => expect(document.title).toBe("Hauskraft"));
  });
});
