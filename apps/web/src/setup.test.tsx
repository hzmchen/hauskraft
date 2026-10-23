// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./app";
import { createI18n } from "./i18n";
import { createAppRouter } from "./router";
import { OWNER_SESSION, fakeApi, json, problem } from "./test/fakeApi";

const OWNER = { ...OWNER_SESSION, user: { ...OWNER_SESSION.user, username: "mia", display_name: "Mia", locale: "de" } };

function start(path: string, { required = true, answer }: { required?: boolean; answer?: () => Response } = {}) {
  const state = { required, signedIn: false, body: null as unknown };
  const calls = fakeApi({
    "GET /api/v1/setup": () => json({ required: state.required }),
    "POST /api/v1/setup": async (request) => {
      state.body = await request.json();
      if (answer) return answer();
      state.required = false;
      state.signedIn = true;
      return json(OWNER, 201);
    },
    "GET /api/v1/auth/session": () => (state.signedIn ? json(OWNER) : problem(401, "unauthenticated")),
    "GET /api/v1/household": () => json({ name: "Familie Müller", timezone: "Europe/Berlin", locale: "de" }),
    "GET /api/v1/themes": () => json([]),
  });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createAppRouter({ initialPath: path, queryClient, i18n: createI18n({ lng: "en" }) });
  render(<App router={router} queryClient={queryClient} />);
  return { router, state, calls };
}

async function fill(repeat = "mia-household-pass-2026") {
  await userEvent.type(await screen.findByRole("textbox", { name: "Household name" }), "Familie Müller");
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "Language" }), "Deutsch");
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "Time zone" }), "Europe/Berlin");
  await userEvent.type(screen.getByRole("textbox", { name: "Your name" }), "Mia");
  await userEvent.type(screen.getByRole("textbox", { name: "Username" }), "mia");
  await userEvent.type(screen.getByLabelText("Password", { exact: true }), "mia-household-pass-2026");
  await userEvent.type(screen.getByLabelText("Repeat password", { exact: true }), repeat);
  await userEvent.click(screen.getByRole("button", { name: "Create household" }));
}

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

describe("setup wizard (M1S-E03-02)", () => {
  it.each(["/", "/login", "/today", "/settings/members"])(
    "sends %s to /setup while setup is required",
    async (path) => {
      const { router } = start(path);
      expect(await screen.findByRole("heading", { level: 1, name: "Set up your household" })).toBeDefined();
      expect(router.state.location.pathname).toBe("/setup");
      expect(screen.getByText("At least 12 characters")).toBeDefined();
      expect(screen.getByLabelText("Password", { exact: true }).getAttribute("autocomplete")).toBe("new-password");
      expect(screen.getByLabelText("Repeat password", { exact: true }).getAttribute("autocomplete")).toBe(
        "new-password",
      );
      expect(screen.getByRole("textbox", { name: "Username" }).getAttribute("autocomplete")).toBe("username");
    },
  );

  it("defaults the time zone to the browser's", async () => {
    start("/setup");
    const zone = (await screen.findByRole("combobox", { name: "Time zone" })) as HTMLSelectElement;
    expect(zone.value).toBe(Intl.DateTimeFormat().resolvedOptions().timeZone);
  });

  it("catches mismatched passwords without a request", async () => {
    const { calls } = start("/setup");
    await fill("something-else-entirely");
    expect((await screen.findByRole("alert")).textContent).toBe("Passwords do not match");
    expect(calls.some((r) => r.method === "POST")).toBe(false);
  });

  it("creates the household and lands on Today, signed in, in the chosen language", async () => {
    const { router, state } = start("/setup");
    await fill();
    await waitFor(() => expect(router.state.location.pathname).toBe("/today"));
    expect(await screen.findByRole("heading", { level: 1, name: "Heute" })).toBeDefined();
    expect(state.body).toEqual({
      household: { name: "Familie Müller", timezone: "Europe/Berlin", locale: "de" },
      owner: { username: "mia", display_name: "Mia", password: "mia-household-pass-2026" },
    });
  });

  it("shows an API error next to its field", async () => {
    start("/setup", { answer: () => problem(422, "invalid_username") });
    await fill();
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Usernames have 2 to 32 characters: a–z, 0–9, '.', '_' or '-'.");
    expect(screen.getByRole("textbox", { name: "Username" }).getAttribute("aria-describedby")).toContain(alert.id);
  });

  it("is closed once the household exists", async () => {
    const { router } = start("/setup", { required: false });
    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
  });
});
