// SPDX-License-Identifier: MIT
import { HostProvider, type Host } from "@hauskraft/sdk-ts";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { fakeApi, json, page, renderWithPlugin, task } from "../test/harness";
import { TasksPage } from "./TasksPage";

function host(search: Record<string, string> = {}) {
  return {
    navigate: vi.fn<Host["navigate"]>(),
    search,
    setSearch: vi.fn<Host["setSearch"]>(),
    timeZone: "Europe/Berlin",
  } satisfies Host;
}

async function show(h: Host, routes: Parameters<typeof fakeApi>[0]) {
  const calls = fakeApi(routes);
  await renderWithPlugin(
    <HostProvider host={h}>
      <TasksPage pluginId="dev.hauskraft.tasks" />
    </HostProvider>,
  );
  return calls;
}

const LIST = (status: string, sort = "-created_at", offset = 0) =>
  `GET /api/v1/tasks?status=${status}&sort=${sort}&limit=50&offset=${offset}`;

afterEach(() => vi.unstubAllGlobals());

describe("All tasks page", () => {
  it("shows open tasks by default with Open, Done and All tabs", async () => {
    await show(host(), { [LIST("open")]: () => page([task("Water the plants")]) });
    expect(screen.getByRole("heading", { level: 1, name: "All tasks" })).toBeDefined();
    expect(screen.getByRole("tab", { name: "Open" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("tab", { name: "Done" })).toBeDefined();
    expect(screen.getByRole("tab", { name: "All" })).toBeDefined();
    expect(await screen.findByRole("checkbox", { name: "Mark 'Water the plants' as done" })).toBeDefined();
  });

  it("keeps filter and sort in the URL, ignoring invalid values", async () => {
    const h = host({ status: "bogus", sort: "due", page: "x" });
    await show(h, { [LIST("open", "due_on")]: () => page([]) });
    await userEvent.click(screen.getByRole("tab", { name: "Done" }));
    expect(h.setSearch).toHaveBeenCalledWith({ status: "done", page: undefined });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Sort by" }), "Created");
    expect(h.setSearch).toHaveBeenCalledWith({ sort: "created", page: undefined });
  });

  it("sets and clears a due date as YYYY-MM-DD", async () => {
    const calls = await show(host(), {
      [LIST("open")]: () => page([task("Recycling", { due_on: "2026-10-20" })]),
      "PATCH /api/v1/tasks/id-Recycling": () => json(task("Recycling")),
    });
    const input = (await screen.findByLabelText("Due date for 'Recycling'")) as HTMLInputElement;
    expect(input.type).toBe("date");
    expect(input.value).toBe("2026-10-20");
    await userEvent.click(screen.getByRole("button", { name: "Clear due date for 'Recycling'" }));
    await waitFor(() => expect(calls.filter((r) => r.method === "PATCH")).toHaveLength(1));
    expect(await calls.find((r) => r.method === "PATCH")!.json()).toEqual({ due_on: null });
  });

  it("asks before deleting; Cancel keeps the task", async () => {
    const calls = await show(host(), {
      [LIST("open")]: () => page([task("Old")]),
      "DELETE /api/v1/tasks/id-Old": () => new Response(null, { status: 204 }),
    });
    await userEvent.click(await screen.findByRole("button", { name: "Delete 'Old'" }));
    let dialog = screen.getByRole("dialog", { name: "Delete task?" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(calls.some((r) => r.method === "DELETE")).toBe(false);

    await userEvent.click(screen.getByRole("button", { name: "Delete 'Old'" }));
    dialog = screen.getByRole("dialog", { name: "Delete task?" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(calls.some((r) => r.method === "DELETE")).toBe(true));
  });

  it("pages 50 at a time", async () => {
    const h = host({ status: "all", page: "2" });
    await show(h, {
      [LIST("all", "-created_at", 50)]: () => json({ items: [task("Item 51")], total: 120, limit: 50, offset: 50 }),
    });
    const pager = await screen.findByRole("navigation", { name: "Pagination" });
    await userEvent.click(within(pager).getByRole("button", { name: "Next page" }));
    expect(h.setSearch).toHaveBeenCalledWith({ page: "3" });
    await userEvent.click(within(pager).getByRole("button", { name: "Previous page" }));
    expect(h.setSearch).toHaveBeenCalledWith({ page: "1" });
  });

  it("has an empty state in words", async () => {
    await show(host(), { [LIST("open")]: () => page([]) });
    expect(await screen.findByText("No tasks yet")).toBeDefined();
  });
});
