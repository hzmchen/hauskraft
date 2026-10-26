// SPDX-License-Identifier: AGPL-3.0-or-later
// M2S-E07-01..03: Settings → Assistant (owners): endpoint, connection test, tool switches and usage.
import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../app";
import { createI18n } from "../i18n";
import { createAppRouter } from "../router";
import { OWNER_SESSION, fakeApi, json, problem } from "../test/fakeApi";

const SETTINGS = {
  configured: true,
  chat: {
    base_url: "http://fake-llm:8090/v1",
    model: "fake-tools",
    api_key_set: true,
    api_key_hint: "…abcd",
    api_key_status: "ok",
    locality: "cloud",
    max_data_class: "household",
    temperature: null,
    max_tokens: null,
    parallel_tool_calls: null,
  },
  tools_disabled: [],
  prices: { input_per_million: null, output_per_million: null, currency: "EUR" },
};
const TOOL = (name: string, read_only: boolean, destructive: boolean, enabled = true) => ({
  name,
  wire_name: name.replace(".", "_"),
  plugin_id: "dev.hauskraft.tasks",
  description: `${name} tool`,
  annotations: { read_only, destructive, idempotent: true, open_world: false },
  data_class: "household",
  permission: "task.read",
  enabled,
});
const USAGE = (group_by: string) => ({
  from: "2026-10-01",
  to: "2026-10-26",
  group_by,
  totals: { requests: 3, input_tokens: 300, output_tokens: 30, unknown_requests: 1, cost: null },
  groups: [
    {
      key: "k",
      label: group_by === "user" ? "Demo Adult" : group_by === "model" ? "fake-tools" : "2026-10-26",
      requests: 3,
      input_tokens: 300,
      output_tokens: 30,
      unknown_requests: 1,
    },
  ],
});

type Routes = Parameters<typeof fakeApi>[0];

function start(extra: Routes = {}) {
  const patches: unknown[] = [];
  fakeApi({
    "GET /api/v1/auth/session": () => json(OWNER_SESSION),
    "GET /api/v1/themes": () => json([]),
    "GET /api/v1/assistant/status": () => json({ available: true }),
    "GET /api/v1/assistant/settings": () => json(SETTINGS),
    "GET /api/v1/assistant/tools": () => json([TOOL("tasks.delete", false, true), TOOL("tasks.list", true, false)]),
    "GET /api/v1/assistant/usage": (r) => json(USAGE(new URL(r.url).searchParams.get("group_by") ?? "day")),
    "PATCH /api/v1/assistant/settings": async (r) => {
      patches.push(await r.json());
      return json(SETTINGS);
    },
    "POST /api/v1/assistant/settings/test": () =>
      json({
        ok: false,
        checks: { reachable: true, auth: false, model: false, tool_calls: false },
        latency_ms: 5,
        error_code: "auth_failed",
      }),
    ...extra,
  });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createAppRouter({ initialPath: "/settings/assistant", queryClient, i18n: createI18n({ lng: "en" }) });
  render(<App router={router} queryClient={queryClient} />);
  return patches;
}

const region = (name: string) => screen.getByRole("region", { name });

afterEach(() => vi.unstubAllGlobals());

describe("Settings → Assistant (M2S-E07)", () => {
  it("shows the endpoint with only the key's last four characters", async () => {
    start();
    expect(await screen.findByRole("heading", { level: 1, name: "Assistant" })).toBeDefined();
    const endpoint = region("Endpoint");
    expect((within(endpoint).getByRole("textbox", { name: "Base URL" }) as HTMLInputElement).value).toBe(
      "http://fake-llm:8090/v1",
    );
    expect(within(endpoint).getByText(/Saved key ends in abcd/)).toBeDefined();
    expect((within(endpoint).getByLabelText("API key", { exact: true }) as HTMLInputElement).value).toBe("");
  });

  it("saves without the key when it is left empty, with it when typed", async () => {
    const patches = start();
    const endpoint = await waitFor(() => region("Endpoint"));
    await userEvent.click(within(endpoint).getByRole("button", { name: "Save endpoint" }));
    expect(await within(endpoint).findByText("Endpoint saved")).toBeDefined();
    expect(patches[0]).toEqual({
      chat: { base_url: "http://fake-llm:8090/v1", model: "fake-tools", locality: "cloud" },
    });
    await userEvent.type(within(endpoint).getByLabelText("API key", { exact: true }), "sk-new-key-9999");
    await userEvent.click(within(endpoint).getByRole("button", { name: "Save endpoint" }));
    await waitFor(() => expect((patches[1] as { chat: { api_key: string } }).chat.api_key).toBe("sk-new-key-9999"));
  });

  it("shows an invalid base URL next to its field", async () => {
    start({ "PATCH /api/v1/assistant/settings": () => problem(422, "invalid_base_url") });
    const endpoint = await waitFor(() => region("Endpoint"));
    await userEvent.click(within(endpoint).getByRole("button", { name: "Save endpoint" }));
    expect((await within(endpoint).findByRole("alert")).textContent).toBe("Enter an absolute http or https URL.");
  });

  it("names each connection check", async () => {
    start();
    const endpoint = await waitFor(() => region("Endpoint"));
    await userEvent.click(within(endpoint).getByRole("button", { name: "Test connection" }));
    const checks = await within(endpoint).findByRole("list", { name: "Connection checks" });
    expect(
      within(checks)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual([
      "Server reachable: OK",
      "API key accepted: Failed",
      "Model found: Failed",
      "Tool calls supported: Failed",
    ]);
  });

  it("switches a tool off", async () => {
    const patches = start();
    const tools = await waitFor(() => region("Tools"));
    const toggle = await within(tools).findByRole("switch", { name: "tasks.delete" });
    expect(toggle.getAttribute("aria-checked")).toBe("true");
    expect(tools.textContent).toContain("Deletes – asks first");
    await userEvent.click(toggle);
    expect(await within(tools).findByText("Tools saved")).toBeDefined();
    expect(patches).toEqual([{ tools_disabled: ["tasks.delete"] }]);
  });

  it("shows usage by day, member and model, with unknown requests", async () => {
    start();
    const usage = await waitFor(() => region("Usage"));
    expect(await within(usage).findByRole("table", { name: "Usage by member" })).toBeDefined();
    await waitFor(() =>
      expect(within(usage).getByRole("table", { name: "Usage by member" }).textContent).toContain("Demo Adult"),
    );
    expect(within(usage).getByRole("table", { name: "Usage by model" }).textContent).toContain("fake-tools");
    expect(within(usage).getByRole("table", { name: "Usage by day" }).textContent).toContain("1 unknown");
  });
});
