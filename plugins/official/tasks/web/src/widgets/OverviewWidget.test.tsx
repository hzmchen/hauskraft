// SPDX-License-Identifier: MIT
// M2S-E06-06: the "Weekly overview" widget shows the person's latest overview and creates a new one.
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { fakeApi, json, renderWithPlugin } from "../test/harness";
import { OverviewWidget } from "./OverviewWidget";

const RUN = { id: "r1", kind: "skill", status: "done", error_code: null, channel: "text" };
const LATEST = "GET /api/v1/assistant/skills/tasks.weekly-overview/runs/latest";

afterEach(() => vi.unstubAllGlobals());

describe("Weekly overview (M2S-E06-06)", () => {
  it("says so when the assistant isn't set up", async () => {
    fakeApi({ "GET /api/v1/assistant/status": () => json({ available: false }) });
    await renderWithPlugin(
      <OverviewWidget pluginId="dev.hauskraft.tasks" instanceId="w1" size={{ w: 4, h: 4 }} config={{}} />,
    );
    expect(await screen.findByText("The assistant isn't set up.")).toBeDefined();
    expect(screen.queryByRole("button", { name: "Create now" })).toBeNull();
  });

  it("starts empty and creates an overview", async () => {
    fakeApi({
      "GET /api/v1/assistant/status": () => json({ available: true }),
      [LATEST]: () => json({ code: "not_found" }, 404),
      "POST /api/v1/assistant/skills/tasks.weekly-overview/runs": () =>
        json({ run: RUN, created_at: new Date().toISOString(), output: "This week: Buy milk." }),
    });
    await renderWithPlugin(
      <OverviewWidget pluginId="dev.hauskraft.tasks" instanceId="w1" size={{ w: 4, h: 4 }} config={{}} />,
    );
    expect(await screen.findByText("No overview yet.")).toBeDefined();
    await userEvent.click(screen.getByRole("button", { name: "Create now" }));
    expect(await screen.findByText("This week: Buy milk.")).toBeDefined();
    expect(screen.getByText(/^Created /)).toBeDefined();
  });
});
