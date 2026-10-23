// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createI18n } from "../i18n";
import { App } from "../app";
import { createAppRouter } from "../router";
import { OWNER_SESSION, fakeApi, json } from "../test/fakeApi";
import { TodayDashboard } from "./Today";

const LAYOUT = [
  {
    i: "dev.hauskraft.tasks/tasks.list",
    plugin_id: "dev.hauskraft.tasks",
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

describe("Today freshness", () => {
  it("shows tasks added elsewhere when Today is opened again", async () => {
    let open: { id: string; title: string }[] = [];
    const page = (items: unknown[]) => json({ items, total: items.length, limit: 50, offset: 0 });
    const task = (id: string, title: string) => ({
      id,
      title,
      done: false,
      done_at: null,
      due_on: null,
      data_class: "household",
      version: 1,
      created_by: { id: OWNER_SESSION.user.id, display_name: "Demo Adult" },
      updated_by: { id: OWNER_SESSION.user.id, display_name: "Demo Adult" },
      created_at: "2026-10-23T08:00:00Z",
      updated_at: "2026-10-23T08:00:00Z",
    });
    fakeApi({
      "GET /api/v1/auth/session": () => json(OWNER_SESSION),
      "GET /api/v1/themes": () => json([]),
      "GET /api/v1/dashboard/today": () => json({ dashboard_id: "today", layout: LAYOUT }),
      "GET /api/v1/plugins": () =>
        json([
          {
            id: "dev.hauskraft.tasks",
            kind: "official",
            enabled: true,
            load_error: null,
            contributes: { widgets: [{ id: "tasks.list", title: "i18n:tasks:widget.title" }] },
          },
        ]),
      "GET /api/v1/tasks": (request) =>
        new URL(request.url).searchParams.get("status") === "done"
          ? page([])
          : page(open.map((t) => task(t.id, t.title))),
    });
    vi.stubGlobal("matchMedia", (q: string) => ({
      matches: q.includes("min-width"),
      addEventListener() {},
      removeEventListener() {},
    }));
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 10_000 } } });
    const router = createAppRouter({ initialPath: "/today", queryClient, i18n: createI18n({ lng: "en" }) });
    render(<App router={router} queryClient={queryClient} />);
    expect(await screen.findByText("0 open")).toBeDefined();
    // Added in another browser within the default stale time (basics step 10 on CI).
    open = [{ id: "0199f391-4444-7aaa-8bbb-000000000001", title: "Plan the garden" }];
    await router.navigate({ to: "/settings/appearance" });
    await router.navigate({ to: "/today" });
    expect(await screen.findByText("Plan the garden")).toBeDefined();
  });
});
