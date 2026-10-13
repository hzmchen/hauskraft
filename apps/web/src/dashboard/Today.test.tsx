// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createI18n } from "../i18n";
import { fakeApi, json } from "../test/fakeApi";
import { TodayDashboard } from "./Today";

const LAYOUT = [
  {
    i: "org.hearthos.tasks/tasks.list",
    plugin_id: "org.hearthos.tasks",
    widget_id: "tasks.list",
    x: 0,
    y: 0,
    w: 4,
    h: 6,
  },
];
let puts: unknown[];

async function show(wide = true) {
  puts = [];
  vi.stubGlobal("matchMedia", (q: string) => ({
    matches: q.includes("min-width") ? wide : false,
    addEventListener() {},
    removeEventListener() {},
  }));
  fakeApi({
    "GET /api/v1/dashboard/today": () => json({ dashboard_id: "today", layout: LAYOUT }),
    "PUT /api/v1/dashboard/today": async (r) => {
      puts.push(await r.json());
      return json({ dashboard_id: "today", layout: LAYOUT });
    },
    "GET /api/v1/plugins": () => json([]),
  });
  await act(async () => {
    render(
      <I18nextProvider i18n={createI18n({ lng: "en" })}>
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
          <TodayDashboard />
        </QueryClientProvider>
      </I18nextProvider>,
    );
  });
}

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

describe("Today", () => {
  it("shows the heading and every widget of the layout", async () => {
    await show();
    expect(screen.getByRole("heading", { level: 1, name: "Today" })).toBeDefined();
    // The tasks plugin is not enabled in this fake, so its cell shows the unavailable card.
    expect(await screen.findByRole("region", { name: "Widget unavailable" })).toBeDefined();
  });

  it("Edit layout toggles to Done editing, which saves the layout", async () => {
    await show();
    await userEvent.click(await screen.findByRole("button", { name: "Edit layout" }));
    await userEvent.click(screen.getByRole("button", { name: "Done editing" }));
    await vi.waitFor(() => expect(puts).toEqual([{ layout: LAYOUT }]));
    expect(screen.getByRole("button", { name: "Edit layout" })).toBeDefined();
  });

  it("stacks widgets in one column on narrow screens, without editing", async () => {
    await show(false);
    expect(await screen.findByRole("region", { name: "Widget unavailable" })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Edit layout" })).toBeNull();
  });
});
