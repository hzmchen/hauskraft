// SPDX-License-Identifier: MIT
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { fakeApi, json, page, renderWithPlugin, task } from "../test/harness";
import { TasksWidget } from "./TasksWidget";

const props = { instanceId: "w1", pluginId: "org.hearthos.tasks", size: { w: 4, h: 6 }, config: {} };
const OPEN = "GET /api/v1/tasks?status=open&sort=-created_at&limit=50";
const DONE = "GET /api/v1/tasks?status=done&sort=-created_at&limit=50";

afterEach(() => vi.unstubAllGlobals());

const openList = () => screen.getByRole("list", { name: "Open tasks" });
const box = (title: string) => screen.getByRole("checkbox", { name: `Mark '${title}' as done` });

describe("TasksWidget", () => {
  it("lists open tasks with a done counter and a link to all tasks", async () => {
    fakeApi({ [OPEN]: () => page([task("Water the plants")]), [DONE]: () => page([task("Old", { done: true })]) });
    await renderWithPlugin(<TasksWidget {...props} />);
    expect(await within(openList()).findByRole("checkbox", { name: "Mark 'Water the plants' as done" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Show done (1)" })).toBeDefined();
    expect(screen.getByRole("link", { name: /All tasks/ }).getAttribute("href")).toBe("/p/tasks");
  });

  it("adds a task on Enter, on top, before the server answers, and clears the input", async () => {
    let answer: (r: Response) => void = () => undefined;
    const calls = fakeApi({
      [OPEN]: () => page([task("Older")]),
      [DONE]: () => page([]),
      "POST /api/v1/tasks": () => new Promise<Response>((resolve) => (answer = resolve)),
    });
    await renderWithPlugin(<TasksWidget {...props} />);
    const input = await screen.findByRole("textbox", { name: "Add a task" });
    await userEvent.type(input, "Buy milk{Enter}");
    expect((input as HTMLInputElement).value).toBe("");
    const first = within(openList()).getAllByRole("listitem")[0]!;
    expect(within(first).getByRole("checkbox", { name: "Mark 'Buy milk' as done" })).toBeDefined();
    answer(json(task("Buy milk"), 201));
    const post = calls.find((r) => r.method === "POST")!;
    expect(await post.json()).toEqual({ title: "Buy milk" });
  });

  it("does not send an empty title", async () => {
    const calls = fakeApi({ [OPEN]: () => page([]), [DONE]: () => page([]) });
    await renderWithPlugin(<TasksWidget {...props} />);
    await userEvent.type(await screen.findByRole("textbox", { name: "Add a task" }), "   {Enter}");
    expect(calls.some((r) => r.method === "POST")).toBe(false);
  });

  it("rolls back an add the server rejects", async () => {
    fakeApi({
      [OPEN]: () => page([]),
      [DONE]: () => page([]),
      "POST /api/v1/tasks": () => json({ code: "validation_failed", status: 422 }, 422),
    });
    await renderWithPlugin(<TasksWidget {...props} />);
    await userEvent.type(await screen.findByRole("textbox", { name: "Add a task" }), "Too long{Enter}");
    await waitFor(() => expect(screen.queryByRole("checkbox", { name: "Mark 'Too long' as done" })).toBeNull());
  });

  it("ticking a task marks it done", async () => {
    let done = false;
    const calls = fakeApi({
      [OPEN]: () => page(done ? [] : [task("Water the plants")]),
      [DONE]: () => page(done ? [task("Water the plants", { done: true })] : []),
      "PATCH /api/v1/tasks/id-Water-the-plants": () => {
        done = true;
        return json(task("Water the plants", { done: true, version: 2 }));
      },
    });
    await renderWithPlugin(<TasksWidget {...props} />);
    await userEvent.click(await screen.findByRole("checkbox", { name: "Mark 'Water the plants' as done" }));
    await waitFor(() => expect(calls.some((r) => r.method === "PATCH")).toBe(true));
    expect(await calls.find((r) => r.method === "PATCH")!.json()).toEqual({ done: true });
    await waitFor(() => expect(within(openList()).queryByRole("checkbox", { name: /Water the plants/ })).toBeNull());
  });

  it("renames inline: Enter saves, Escape cancels", async () => {
    let stored = "Buy milk";
    const calls = fakeApi({
      [OPEN]: () => page([task(stored, { id: "id-Buy-milk" })]),
      [DONE]: () => page([]),
      "PATCH /api/v1/tasks/id-Buy-milk": () => {
        stored = "Buy oat milk";
        return json(task(stored, { id: "id-Buy-milk", version: 2 }));
      },
    });
    await renderWithPlugin(<TasksWidget {...props} />);
    await userEvent.click(await screen.findByRole("button", { name: "Edit 'Buy milk'" }));
    await userEvent.keyboard("{Escape}");
    expect(calls.some((r) => r.method === "PATCH")).toBe(false);
    expect(box("Buy milk")).toBeDefined();

    await userEvent.click(screen.getByRole("button", { name: "Edit 'Buy milk'" }));
    const title = screen.getByRole("textbox", { name: "Task title" });
    await userEvent.clear(title);
    await userEvent.type(title, "Buy oat milk{Enter}");
    expect(box("Buy oat milk")).toBeDefined();
    expect(await calls.find((r) => r.method === "PATCH")!.json()).toEqual({ title: "Buy oat milk" });
  });

  it("shows due badges in words", async () => {
    const today = new Date();
    const iso = (d: Date) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    const yesterday = new Date(today.getTime() - 86_400_000);
    fakeApi({
      [OPEN]: () => page([task("A", { due_on: iso(yesterday) }), task("B", { due_on: iso(today) })]),
      [DONE]: () => page([]),
    });
    await renderWithPlugin(<TasksWidget {...props} />);
    const rows = await within(openList()).findAllByRole("listitem");
    expect(rows[0]!.textContent).toContain("Overdue");
    expect(rows[1]!.textContent).toContain("Today");
  });

  it("the done list appears after Show done", async () => {
    fakeApi({ [OPEN]: () => page([]), [DONE]: () => page([task("Old", { done: true })]) });
    await renderWithPlugin(<TasksWidget {...props} />);
    await userEvent.click(await screen.findByRole("button", { name: "Show done (1)" }));
    const done = screen.getByRole("list", { name: "Done tasks" });
    expect(within(done).getByRole("checkbox", { name: "Mark 'Old' as done" }).getAttribute("aria-checked")).toBe(
      "true",
    );
  });
});
