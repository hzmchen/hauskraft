// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../app";
import { createI18n } from "../i18n";
import { createAppRouter } from "../router";
import { DEMO_SESSION, OWNER_SESSION, fakeApi, json } from "../test/fakeApi";

function start(path: string, session: unknown, lng: "en" | "de" = "en") {
  fakeApi({
    "GET /api/v1/auth/session": () => json(session),
    "GET /api/v1/themes": () => json([]),
    "GET /api/v1/me": () => json((session as typeof DEMO_SESSION).user),
    "GET /api/v1/me/sessions": () => json([]),
    "GET /api/v1/household": () => json({ name: "Demo household", timezone: "Europe/Berlin", locale: "en" }),
    "GET /api/v1/users": () => json([]),
  });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createAppRouter({ initialPath: path, queryClient, i18n: createI18n({ lng }) });
  render(<App router={router} queryClient={queryClient} />);
  return router;
}

async function sections(): Promise<string[]> {
  const nav = await screen.findByRole("navigation", { name: "Settings" });
  return within(nav)
    .getAllByRole("link")
    .map((a) => a.textContent ?? "");
}

afterEach(() => vi.unstubAllGlobals());

describe("settings layout (M1S-E08-01)", () => {
  it("shows owners four sections, each with its own level-1 heading", async () => {
    start("/settings/appearance", OWNER_SESSION);
    expect(await sections()).toEqual(["Appearance", "Account", "Household", "Members"]);
    for (const name of ["Account", "Household", "Members", "Appearance"]) {
      const nav = screen.getByRole("navigation", { name: "Settings" });
      await userEvent.click(within(nav).getByRole("link", { name }));
      expect(await screen.findByRole("heading", { level: 1, name })).toBeDefined();
    }
  });

  it("shows adults Appearance and Account only and sends them away from owner sections", async () => {
    const router = start("/settings/household", DEMO_SESSION);
    expect(await sections()).toEqual(["Appearance", "Account"]);
    await waitFor(() => expect(router.state.location.pathname).toBe("/settings/appearance"));
    await router.navigate({ to: "/settings/members" });
    await waitFor(() => expect(router.state.location.pathname).toBe("/settings/appearance"));
  });

  it("translates the section names", async () => {
    start("/settings/appearance", { ...OWNER_SESSION, user: { ...OWNER_SESSION.user, locale: "de" } }, "de");
    expect(await sections()).toEqual(["Darstellung", "Konto", "Haushalt", "Mitglieder"]);
  });

  it("keeps /settings opening Appearance", async () => {
    const router = start("/settings", DEMO_SESSION);
    await waitFor(() => expect(router.state.location.pathname).toBe("/settings/appearance"));
  });
});
