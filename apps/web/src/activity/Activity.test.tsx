// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createI18n } from "../i18n";
import { fakeApi, json } from "../test/fakeApi";
import { ActivityFeed } from "./Activity";

const demo = { id: "0199f390-1111-7aaa-8bbb-cccccccccccc", display_name: "Demo Adult" };
const item = (n: number, type: string, data: unknown, actor: typeof demo | null = demo) => ({
  id: `0199f390-0000-7000-8000-${String(n).padStart(12, "0")}`,
  type,
  time: `2026-10-13T10:${String(59 - n).padStart(2, "0")}:00Z`,
  actor,
  subject: "task/1",
  summary_key: `activity.${type.replace("hearthos.", "")}`,
  data,
});
const task = (title: string) => ({ task: { id: "1", title, done: false, due_on: null, version: 1 } });

async function show(lng: "en" | "de" = "en", extraPage: unknown[] = []) {
  const first = [
    item(1, "hearthos.task.created", task("Buy milk")),
    item(2, "hearthos.task.updated", {
      ...task("Buy oat milk"),
      changes: { title: { from: "Buy milk", to: "Buy oat milk" } },
    }),
    item(3, "hearthos.task.completed", { ...task("Buy oat milk"), completed_at: "2026-10-13T10:00:00Z" }),
    item(4, "hearthos.task.deleted", task("Buy oat milk")),
    item(5, "hearthos.settings.theme_changed", {
      from: "org.hearthos.theme.default",
      to: "org.hearthos.theme.hackspace",
    }),
    item(6, "hearthos.plugin.toggled", { plugin_id: "org.example.x", enabled: false }, null),
  ];
  const calls = fakeApi({
    "GET /api/v1/activity": (r) => json(new URL(r.url).searchParams.has("before") ? extraPage : first),
    "GET /api/v1/themes": () => json([{ theme_id: "org.hearthos.theme.hackspace", name: "Hackspace" }]),
  });
  await act(async () => {
    render(
      <I18nextProvider i18n={createI18n({ lng })}>
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
          <ActivityFeed />
        </QueryClientProvider>
      </I18nextProvider>,
    );
  });
  return calls;
}

afterEach(() => vi.unstubAllGlobals());

describe("Activity", () => {
  it("summarises who did what, newest first", async () => {
    await show();
    expect(screen.getByRole("heading", { level: 1, name: "Activity" })).toBeDefined();
    const feed = await screen.findByRole("list", { name: "Activity" });
    await vi.waitFor(() => expect(within(feed).getAllByRole("listitem")).toHaveLength(6));
    const texts = within(feed)
      .getAllByRole("listitem")
      .map((li) => li.textContent ?? "");
    expect(texts[0]).toContain("Demo Adult added 'Buy milk'");
    expect(texts[1]).toContain("Demo Adult updated 'Buy oat milk'");
    expect(texts[2]).toContain("Demo Adult completed 'Buy oat milk'");
    expect(texts[3]).toContain("Demo Adult deleted 'Buy oat milk'");
    await vi.waitFor(() =>
      expect(texts[4] && within(feed).getAllByRole("listitem")[4]!.textContent).toContain(
        "Demo Adult switched the theme to Hackspace",
      ),
    );
    expect(texts[5]).toContain("HearthOS turned off org.example.x");
    expect(within(feed).getAllByRole("listitem")[0]!.textContent).toMatch(/Oct 13, 2026/);
  });

  it("speaks German", async () => {
    await show("de");
    const feed = await screen.findByRole("list", { name: "Aktivität" });
    await vi.waitFor(() =>
      expect(within(feed).getAllByRole("listitem")[0]!.textContent).toContain("Demo Adult hat 'Buy milk' hinzugefügt"),
    );
  });

  it("loads older entries on request", async () => {
    const calls = await show("en", [item(9, "hearthos.task.created", task("Ancient"))]);
    await userEvent.click(await screen.findByRole("button", { name: "Show older" }));
    expect(await screen.findByText(/added 'Ancient'/)).toBeDefined();
    const older = calls.find((r) => new URL(r.url).searchParams.has("before"))!;
    expect(new URL(older.url).searchParams.get("before")).toBe("2026-10-13T10:53:00Z");
  });
});
