// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../app";
import { createI18n } from "../i18n";
import { createAppRouter } from "../router";
import { OWNER_SESSION, fakeApi, json, problem } from "../test/fakeApi";

const HOUSEHOLD = { name: "Demo household", timezone: "Europe/Berlin", locale: "en" };

function start(patch: (body: Record<string, unknown>) => Response) {
  const sent: unknown[] = [];
  fakeApi({
    "GET /api/v1/auth/session": () => json(OWNER_SESSION),
    "GET /api/v1/themes": () => json([]),
    "GET /api/v1/household": () => json(HOUSEHOLD),
    "PATCH /api/v1/household": async (request) => {
      const body = (await request.json()) as Record<string, unknown>;
      sent.push(body);
      return patch(body);
    },
  });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createAppRouter({ initialPath: "/settings/household", queryClient, i18n: createI18n({ lng: "en" }) });
  render(<App router={router} queryClient={queryClient} />);
  return sent;
}

afterEach(() => vi.unstubAllGlobals());

describe("Settings → Household (M1S-E04-02)", () => {
  it("shows and saves the household name, time zone and default language", async () => {
    const sent = start((body) => json({ ...HOUSEHOLD, ...body }));
    expect(await screen.findByRole("heading", { level: 1, name: "Household" })).toBeDefined();
    const name = (await screen.findByRole("textbox", { name: "Household name" })) as HTMLInputElement;
    await vi.waitFor(() => expect(name.value).toBe("Demo household"));
    const zone = screen.getByRole("combobox", { name: "Time zone" }) as HTMLSelectElement;
    expect(zone.value).toBe("Europe/Berlin");
    expect(screen.getByText("Used for new members")).toBeDefined();
    await userEvent.clear(name);
    await userEvent.type(name, "Familie Müller");
    await userEvent.selectOptions(zone, "Pacific/Kiritimati");
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Default language" }), "Deutsch");
    await userEvent.click(screen.getByRole("button", { name: "Save household" }));
    expect(await screen.findByText("Household saved")).toBeDefined();
    expect(sent).toEqual([{ name: "Familie Müller", timezone: "Pacific/Kiritimati", locale: "de" }]);
  });

  it("shows an unknown time zone next to the field", async () => {
    start(() => problem(422, "invalid_timezone"));
    await userEvent.click(await screen.findByRole("button", { name: "Save household" }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Choose a time zone from the list.");
    expect(screen.getByRole("combobox", { name: "Time zone" }).getAttribute("aria-describedby")).toContain(alert.id);
    expect(screen.queryByText("Household saved")).toBeNull();
  });
});
