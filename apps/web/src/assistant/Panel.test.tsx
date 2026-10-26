// SPDX-License-Identifier: AGPL-3.0-or-later
// M2S-E06-01..04: the assistant's button and side panel, chats, messages, errors and cards.
import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../app";
import { createI18n } from "../i18n";
import { createAppRouter } from "../router";
import { DEMO_SESSION, fakeApi, json, problem } from "../test/fakeApi";

type Routes = Parameters<typeof fakeApi>[0];
const RUN = "0199f3a0-0000-7000-8000-000000000001";
const CHAT = "0199f3a0-0000-7000-8000-0000000000c1";
const now = "2026-10-26T10:00:00Z";
const msg = (id: string, role: "user" | "assistant", text: string) => ({
  id,
  role,
  text,
  run_id: RUN,
  created_at: now,
});
const run = (status = "done", error_code: string | null = null) => ({
  id: RUN,
  kind: "chat",
  status,
  error_code,
  channel: "text",
});
const added = {
  id: "0199f3a0-0000-7000-8000-0000000000a1",
  run_id: RUN,
  tool: "tasks.create",
  status: "done",
  summary_key: "tasks:tool.create.done",
  record: { type: "Task", id: "t1", label: "Buy milk" },
  undo_available: true,
  error_code: null,
};

function start(routes: Routes = {}, { available = true, permissions = DEMO_SESSION.permissions } = {}) {
  const sent: { path: string; body: unknown }[] = [];
  let detail = {
    id: CHAT,
    title: null as string | null,
    created_at: now,
    updated_at: now,
    messages: [] as unknown[],
    actions: [] as unknown[],
  };
  fakeApi({
    "GET /api/v1/auth/session": () => json({ ...DEMO_SESSION, permissions }),
    "GET /api/v1/themes": () => json([]),
    // The tasks plugin's strings name the cards ("Added task '…'").
    "GET /api/v1/plugins": () =>
      json([{ id: "dev.hauskraft.tasks", kind: "official", enabled: true, load_error: null, contributes: {} }]),
    "GET /api/v1/dashboard/today": () => json({ dashboard_id: "today", layout: [] }),
    "GET /api/v1/household": () => json({ name: "Home", timezone: "Europe/Berlin", locale: "en" }),
    "GET /api/v1/assistant/status": () => json({ available }),
    "GET /api/v1/assistant/conversations": () =>
      json(detail.title === null && detail.messages.length === 0 ? [] : [detail]),
    "POST /api/v1/assistant/conversations": () => json(detail, 201),
    [`GET /api/v1/assistant/conversations/${CHAT}`]: () => json(detail),
    [`POST /api/v1/assistant/conversations/${CHAT}/messages`]: async (r) => {
      const body = (await r.json()) as { text: string };
      sent.push({ path: "messages", body });
      const messages = [msg("m1", "user", body.text), msg("m2", "assistant", "Added **Buy milk**.")];
      detail = { ...detail, title: body.text, messages, actions: [added] };
      return json({ run: run(), messages, actions: [added], confirmations: [] });
    },
    ...routes,
  });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createAppRouter({ initialPath: "/today", queryClient, i18n: createI18n({ lng: "en" }) });
  render(<App router={router} queryClient={queryClient} />);
  return sent;
}

const panel = () => screen.getByRole("complementary", { name: "Assistant" });

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

describe("assistant panel (M2S-E06)", () => {
  it("has no button when the assistant isn't set up", async () => {
    start({}, { available: false });
    expect(await screen.findByRole("heading", { level: 1, name: "Today" })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Assistant" })).toBeNull();
  });

  it("has no button without the permission", async () => {
    start({}, { permissions: DEMO_SESSION.permissions.filter((p) => p !== "assistant.use") });
    expect(await screen.findByRole("heading", { level: 1, name: "Today" })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Assistant" })).toBeNull();
  });

  it("opens, remembers it on this device, and closes", async () => {
    start();
    const button = await screen.findByRole("button", { name: "Assistant" });
    expect(button.getAttribute("aria-expanded")).toBe("false");
    await userEvent.click(button);
    expect(panel()).toBeDefined();
    expect(button.getAttribute("aria-expanded")).toBe("true");
    expect(localStorage.getItem("hauskraft.assistant.open")).toBe("1");
    await userEvent.click(within(panel()).getByRole("button", { name: "Close assistant" }));
    expect(screen.queryByRole("complementary", { name: "Assistant" })).toBeNull();
    expect(document.activeElement).toBe(button);
  });

  it("sends a message and shows the answer and an action card with Undo", async () => {
    const sent = start();
    await userEvent.click(await screen.findByRole("button", { name: "Assistant" }));
    await userEvent.type(
      within(panel()).getByRole("textbox", { name: "Message the assistant" }),
      "Add 'Buy milk'{Enter}",
    );
    const log = within(panel()).getByRole("log", { name: "Messages" });
    await waitFor(() => expect(log.textContent).toContain("Add 'Buy milk'"));
    await waitFor(() => expect(within(log).getByText("Buy milk", { selector: "strong" })).toBeDefined());
    const card = await within(log).findByRole("article", { name: "Added task 'Buy milk'" });
    expect(within(card).getByRole("button", { name: "Undo" })).toBeDefined();
    expect(sent).toEqual([{ path: "messages", body: { text: "Add 'Buy milk'" } }]);
  });

  it("shows a stable message when the run fails", async () => {
    start({
      [`POST /api/v1/assistant/conversations/${CHAT}/messages`]: () =>
        json({
          run: run("failed", "model_unavailable"),
          messages: [msg("m1", "user", "Hello")],
          actions: [],
          confirmations: [],
        }),
    });
    await userEvent.click(await screen.findByRole("button", { name: "Assistant" }));
    await userEvent.type(within(panel()).getByRole("textbox", { name: "Message the assistant" }), "Hello{Enter}");
    expect((await within(panel()).findByRole("alert")).textContent).toBe(
      "The assistant is not available right now. Try again later.",
    );
  });

  it("asks before deleting and sends the answer", async () => {
    const answers: unknown[] = [];
    const confirmation = {
      id: "call_1",
      run_id: RUN,
      tool: "tasks.delete",
      args: { task_id: "t1" },
      summary_key: "tasks:tool.delete.confirm",
      record: { type: "Task", id: "t1", label: "Buy milk" },
    };
    start({
      [`POST /api/v1/assistant/conversations/${CHAT}/messages`]: () =>
        json({
          run: run("awaiting_confirmation"),
          messages: [msg("m1", "user", "Delete it")],
          actions: [],
          confirmations: [confirmation],
        }),
      [`POST /api/v1/assistant/runs/${RUN}/confirmations`]: async (r) => {
        answers.push(await r.json());
        return json({
          run: run(),
          messages: [msg("m2", "assistant", "I did not delete it.")],
          actions: [],
          confirmations: [],
        });
      },
    });
    await userEvent.click(await screen.findByRole("button", { name: "Assistant" }));
    await userEvent.type(within(panel()).getByRole("textbox", { name: "Message the assistant" }), "Delete it{Enter}");
    const card = await within(panel()).findByRole("article", { name: "Delete task 'Buy milk'?" });
    await userEvent.click(within(card).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(answers).toEqual([{ decisions: [{ id: "call_1", approve: false }] }]));
    await waitFor(() => expect(within(panel()).queryByRole("article", { name: "Delete task 'Buy milk'?" })).toBeNull());
  });

  it("deletes a chat after confirming", async () => {
    let deleted = false;
    start({
      "GET /api/v1/assistant/conversations": () =>
        json(deleted ? [] : [{ id: CHAT, title: "Old chat", created_at: now, updated_at: now }]),
      [`DELETE /api/v1/assistant/conversations/${CHAT}`]: () => {
        deleted = true;
        return new Response(null, { status: 204 });
      },
    });
    await userEvent.click(await screen.findByRole("button", { name: "Assistant" }));
    const chats = within(panel()).getByRole("list", { name: "Chats" });
    await userEvent.click(await within(chats).findByRole("button", { name: "Delete chat 'Old chat'" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Delete chat?" });
    await userEvent.click(within(confirm).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(within(chats).queryByRole("button", { name: "Delete chat 'Old chat'" })).toBeNull());
    expect(deleted).toBe(true);
  });

  it("a 409 answer shows the not-set-up message", async () => {
    start({
      [`POST /api/v1/assistant/conversations/${CHAT}/messages`]: () => problem(409, "assistant_not_configured"),
    });
    await userEvent.click(await screen.findByRole("button", { name: "Assistant" }));
    await userEvent.type(within(panel()).getByRole("textbox", { name: "Message the assistant" }), "Hi{Enter}");
    expect((await within(panel()).findByRole("alert")).textContent).toBe("The assistant isn't set up.");
  });
});
