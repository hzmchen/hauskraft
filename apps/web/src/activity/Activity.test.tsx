// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nextProvider } from "react-i18next";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../app";
import { createI18n } from "../i18n";
import { createAppRouter } from "../router";
import { DEMO_SESSION, fakeApi, json } from "../test/fakeApi";
import { ActivityFeed } from "./Activity";

const demo = { id: "0199f390-1111-7aaa-8bbb-cccccccccccc", display_name: "Demo Adult" };
const item = (n: number, type: string, data: unknown, actor: typeof demo | null = demo) => ({
  id: `0199f390-0000-7000-8000-${String(n).padStart(12, "0")}`,
  type,
  time: `2026-10-13T10:${String(59 - n).padStart(2, "0")}:00Z`,
  actor,
  subject: "task/1",
  summary_key: `activity.${type.replace("hauskraft.", "")}`,
  data,
});
const task = (title: string) => ({ task: { id: "1", title, done: false, due_on: null, version: 1 } });

async function show(lng: "en" | "de" = "en", extraPage: unknown[] = []) {
  const first = [
    item(1, "hauskraft.task.created", task("Buy milk")),
    item(2, "hauskraft.task.updated", {
      ...task("Buy oat milk"),
      changes: { title: { from: "Buy milk", to: "Buy oat milk" } },
    }),
    item(3, "hauskraft.task.completed", { ...task("Buy oat milk"), completed_at: "2026-10-13T10:00:00Z" }),
    item(4, "hauskraft.task.deleted", task("Buy oat milk")),
    item(5, "hauskraft.settings.theme_changed", {
      from: "dev.hauskraft.theme.default",
      to: "dev.hauskraft.theme.hackspace",
    }),
    item(6, "hauskraft.plugin.toggled", { plugin_id: "org.example.x", enabled: false }, null),
  ];
  const calls = fakeApi({
    "GET /api/v1/activity": (r) => json(new URL(r.url).searchParams.has("before") ? extraPage : first),
    "GET /api/v1/themes": () => json([{ theme_id: "dev.hauskraft.theme.hackspace", name: "Hackspace" }]),
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
    expect(texts[5]).toContain("Hauskraft turned off org.example.x");
    expect(within(feed).getAllByRole("listitem")[0]!.textContent).toMatch(/Oct 13, 2026/);
  });

  it("speaks German", async () => {
    await show("de");
    const feed = await screen.findByRole("list", { name: "Aktivität" });
    await vi.waitFor(() =>
      expect(within(feed).getAllByRole("listitem")[0]!.textContent).toContain("Demo Adult hat 'Buy milk' hinzugefügt"),
    );
  });

  it("says when the assistant acted for someone, in en and de (M2S-E04-07)", async () => {
    const via = (n: number, type: string, data: unknown) => ({ ...item(n, type, data), agentrunid: "run-1" });
    const events = [
      via(1, "hauskraft.task.created", task("Buy milk")),
      via(2, "hauskraft.task.updated", {
        ...task("Oat milk"),
        changes: { title: { from: "Buy milk", to: "Oat milk" } },
      }),
      via(3, "hauskraft.task.completed", { ...task("Oat milk"), completed_at: "2026-10-13T10:00:00Z" }),
      via(4, "hauskraft.task.deleted", task("Oat milk")),
      item(5, "hauskraft.task.created", task("By hand")),
      via(6, "hauskraft.settings.assistant_changed", { changed: ["chat.model"] }),
    ];
    const expected = {
      en: [
        "Demo Adult via assistant added 'Buy milk'",
        "Demo Adult via assistant updated 'Oat milk'",
        "Demo Adult via assistant completed 'Oat milk'",
        "Demo Adult via assistant deleted 'Oat milk'",
        "Demo Adult added 'By hand'",
        "Demo Adult changed the assistant settings",
      ],
      de: [
        "Demo Adult hat über den Assistenten 'Buy milk' hinzugefügt",
        "Demo Adult hat über den Assistenten 'Oat milk' geändert",
        "Demo Adult hat über den Assistenten 'Oat milk' erledigt",
        "Demo Adult hat über den Assistenten 'Oat milk' gelöscht",
        "Demo Adult hat 'By hand' hinzugefügt",
        "Demo Adult hat die Assistent-Einstellungen geändert",
      ],
    };
    for (const lng of ["en", "de"] as const) {
      fakeApi({ "GET /api/v1/activity": () => json(events), "GET /api/v1/themes": () => json([]) });
      const view = render(
        <I18nextProvider i18n={createI18n({ lng })}>
          <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
            <ActivityFeed />
          </QueryClientProvider>
        </I18nextProvider>,
      );
      const feed = await screen.findByRole("list", { name: lng === "en" ? "Activity" : "Aktivität" });
      await vi.waitFor(() => expect(within(feed).getAllByRole("listitem")).toHaveLength(6));
      const texts = within(feed)
        .getAllByRole("listitem")
        .map((li) => li.firstElementChild?.textContent);
      expect(texts).toEqual(expected[lng]);
      view.unmount();
    }
  });

  it("summarises account and household changes in en and de (M1S-E09-02)", async () => {
    const alex = {
      user: { id: "0199f391-3333-7aaa-8bbb-dddddddddddd", username: "alex", display_name: "Alex", role: "adult" },
    };
    const events = [
      item(1, "hauskraft.user.created", alex),
      item(2, "hauskraft.user.updated", { ...alex, changes: { display_name: { from: "Al", to: "Alex" } } }),
      item(3, "hauskraft.user.deactivated", alex),
      item(4, "hauskraft.user.reactivated", alex),
      item(5, "hauskraft.user.password_reset", alex),
      item(6, "hauskraft.user.password_changed", alex, { ...demo, display_name: "Alex" }),
      item(7, "hauskraft.settings.household_changed", { changes: { name: { from: "A", to: "B" } } }),
    ];
    const expected = {
      en: [
        "Demo Adult added Alex to the household",
        "Demo Adult updated the account of Alex",
        "Demo Adult deactivated Alex",
        "Demo Adult reactivated Alex",
        "Demo Adult reset the password of Alex",
        "Alex changed their password",
        "Demo Adult changed the household settings",
      ],
      de: [
        "Demo Adult hat Alex zum Haushalt hinzugefügt",
        "Demo Adult hat das Konto von Alex geändert",
        "Demo Adult hat Alex deaktiviert",
        "Demo Adult hat Alex reaktiviert",
        "Demo Adult hat das Passwort von Alex zurückgesetzt",
        "Alex hat das eigene Passwort geändert",
        "Demo Adult hat die Haushaltseinstellungen geändert",
      ],
    };
    for (const lng of ["en", "de"] as const) {
      fakeApi({ "GET /api/v1/activity": () => json(events), "GET /api/v1/themes": () => json([]) });
      const view = render(
        <I18nextProvider i18n={createI18n({ lng })}>
          <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
            <ActivityFeed />
          </QueryClientProvider>
        </I18nextProvider>,
      );
      const feed = await screen.findByRole("list", { name: lng === "en" ? "Activity" : "Aktivität" });
      await vi.waitFor(() => expect(within(feed).getAllByRole("listitem")).toHaveLength(7));
      const texts = within(feed)
        .getAllByRole("listitem")
        .map((li) => li.firstElementChild?.textContent);
      expect(texts).toEqual(expected[lng]);
      view.unmount();
    }
  });

  it("loads older entries on request", async () => {
    const calls = await show("en", [item(9, "hauskraft.task.created", task("Ancient"))]);
    await userEvent.click(await screen.findByRole("button", { name: "Show older" }));
    expect(await screen.findByText(/added 'Ancient'/)).toBeDefined();
    const older = calls.find((r) => new URL(r.url).searchParams.has("before"))!;
    expect(new URL(older.url).searchParams.get("before")).toBe("2026-10-13T10:53:00Z");
  });
});

describe("Activity freshness", () => {
  it("shows what happened since the last visit when the page is opened again", async () => {
    let items = [item(1, "hauskraft.task.created", task("Buy milk"))];
    fakeApi({
      "GET /api/v1/auth/session": () => json(DEMO_SESSION),
      "GET /api/v1/themes": () => json([]),
      "GET /api/v1/activity": () => json(items),
    });
    // The app's default stale time (main.tsx): a revisit within it must still show new entries.
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 10_000 } } });
    const router = createAppRouter({ initialPath: "/activity", queryClient, i18n: createI18n({ lng: "en" }) });
    render(<App router={router} queryClient={queryClient} />);
    expect(await screen.findByText(/added 'Buy milk'/)).toBeDefined();
    items = [item(0, "hauskraft.task.created", task("Plan the garden")), ...items];
    await act(async () => {
      await router.navigate({ to: "/today" });
    });
    await act(async () => {
      await router.navigate({ to: "/activity" });
    });
    expect(await screen.findByText(/added 'Plan the garden'/)).toBeDefined();
  });
});
