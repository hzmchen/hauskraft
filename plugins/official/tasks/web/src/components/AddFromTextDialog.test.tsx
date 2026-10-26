// SPDX-License-Identifier: MIT
// M2S-E06-05: "Add from text" suggests tasks with the add-from-text skill and creates only the chosen ones.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { fakeApi, json, renderWithPlugin } from "../test/harness";
import { AddFromText } from "./AddFromTextDialog";

const RUN = { id: "r1", kind: "skill", status: "done", error_code: null, channel: "text" };

afterEach(() => vi.unstubAllGlobals());

describe("Add from text (M2S-E06-05)", () => {
  it("is hidden while the assistant isn't set up", async () => {
    fakeApi({ "GET /api/v1/assistant/status": () => json({ available: false }) });
    await renderWithPlugin(<AddFromText />);
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.queryByRole("button", { name: "Add from text" })).toBeNull();
  });

  it("suggests, lets the person pick, and creates the chosen tasks", async () => {
    const created: unknown[] = [];
    const runs: unknown[] = [];
    fakeApi({
      "GET /api/v1/assistant/status": () => json({ available: true }),
      "POST /api/v1/assistant/skills/tasks.add-from-text/runs": async (r) => {
        runs.push(await r.json());
        return json({
          run: RUN,
          created_at: "2026-10-26T10:00:00Z",
          output: {
            tasks: [
              { title: "Buy milk", due_on: null },
              { title: "Call Bob", due_on: "2026-10-27" },
              { title: "Water plants", due_on: null },
            ],
          },
        });
      },
      "POST /api/v1/tasks": async (r) => {
        created.push(await r.json());
        return json({}, 201);
      },
    });
    await renderWithPlugin(<AddFromText />);
    await userEvent.click(await screen.findByRole("button", { name: "Add from text" }));
    const dialog = await screen.findByRole("dialog", { name: "Add tasks from text" });
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Text" }), "- Buy milk");
    await userEvent.click(within(dialog).getByRole("button", { name: "Suggest tasks" }));
    const list = await within(dialog).findByRole("list", { name: "Suggested tasks" });
    expect(within(list).getAllByRole("checkbox")).toHaveLength(3);
    await userEvent.click(within(list).getByRole("checkbox", { name: "Water plants" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Add 2 tasks" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Add tasks from text" })).toBeNull());
    expect(runs).toEqual([{ input: { text: "- Buy milk" } }]);
    expect(created).toEqual([{ title: "Buy milk" }, { title: "Call Bob", due_on: "2026-10-27" }]);
  });
});
