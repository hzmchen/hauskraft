// SPDX-License-Identifier: AGPL-3.0-or-later
import type { PluginWebModule } from "@hauskraft/sdk-ts";
import { act, render, screen } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createI18n } from "../i18n";
import { PluginWidget, type PluginLoaders } from "./PluginWidget";

const ok: PluginWebModule = {
  widgets: { "tasks.list": ({ instanceId }) => <p>widget {instanceId}</p> },
  pages: {},
  locales: { en: { title: "Tasks" }, de: { title: "Aufgaben" } },
};

async function show(loaders: PluginLoaders, enabled: string[], widgetId = "tasks.list") {
  const i18n = createI18n({ lng: "en" });
  // React 19: a component that suspends on first render needs an awaited act().
  await act(async () => {
    render(
      <I18nextProvider i18n={i18n}>
        <PluginWidget
          loaders={loaders}
          enabled={new Set(enabled)}
          pluginId="dev.hauskraft.tasks"
          widgetId={widgetId}
          instanceId="w1"
          size={{ w: 4, h: 6 }}
        />
      </I18nextProvider>,
    );
  });
  return i18n;
}

afterEach(() => vi.restoreAllMocks());

describe("PluginWidget", () => {
  it("renders an enabled plugin's widget and registers its strings", async () => {
    const i18n = await show({ "dev.hauskraft.tasks": async () => ({ default: ok }) }, ["dev.hauskraft.tasks"]);
    expect(await screen.findByText("widget w1")).toBeDefined();
    expect(i18n.t("tasks:title")).toBe("Tasks");
  });

  it.each([
    ["the plugin is not in the registry", {}, ["dev.hauskraft.tasks"], "tasks.list"],
    ["the plugin is disabled", { "dev.hauskraft.tasks": async () => ({ default: ok }) }, [], "tasks.list"],
    [
      "the widget id is unknown",
      { "dev.hauskraft.tasks": async () => ({ default: ok }) },
      ["dev.hauskraft.tasks"],
      "nope",
    ],
  ] as const)("shows 'Widget unavailable' when %s", async (_, loaders, enabled, widgetId) => {
    await show(loaders as PluginLoaders, [...enabled], widgetId);
    expect(await screen.findByRole("region", { name: "Widget unavailable" })).toBeDefined();
  });

  it("contains a crashing widget", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const broken: PluginWebModule = {
      ...ok,
      widgets: {
        "tasks.list": () => {
          throw new Error("boom");
        },
      },
    };
    await show({ "dev.hauskraft.tasks": async () => ({ default: broken }) }, ["dev.hauskraft.tasks"]);
    expect(await screen.findByRole("region", { name: "Widget unavailable" })).toBeDefined();
  });
});
