// SPDX-License-Identifier: AGPL-3.0-or-later
import type { PluginOut, PluginWebModule } from "@hearthos/sdk-ts";
import { RouterProvider, createMemoryHistory, createRootRoute, createRouter } from "@tanstack/react-router";
import { act, render, screen } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import { describe, expect, it } from "vitest";

import { createI18n } from "../i18n";
import { PluginPage } from "./PluginPage";

const tasks = {
  id: "org.hearthos.tasks",
  enabled: true,
  load_error: null,
  contributes: { pages: [{ id: "tasks", title: "i18n:tasks:page.title", component: "TasksPage", nav: true }] },
} as unknown as PluginOut;

const module: PluginWebModule = {
  widgets: {},
  pages: { TasksPage: ({ pluginId }) => <h1>All tasks of {pluginId}</h1> },
  locales: { en: {}, de: {} },
};

async function show(pageId: string) {
  const loaders = { "org.hearthos.tasks": async () => ({ default: module }) };
  const router = createRouter({
    routeTree: createRootRoute({ component: () => <PluginPage pageId={pageId} plugins={[tasks]} loaders={loaders} /> }),
    history: createMemoryHistory({ initialEntries: [`/p/${pageId}`] }),
  });
  await act(async () => {
    render(
      <I18nextProvider i18n={createI18n({ lng: "en" })}>
        <RouterProvider router={router} />
      </I18nextProvider>,
    );
  });
}

describe("PluginPage", () => {
  it("renders the page component the manifest names", async () => {
    await show("tasks");
    expect(await screen.findByRole("heading", { level: 1, name: "All tasks of org.hearthos.tasks" })).toBeDefined();
  });

  it("answers unknown pages with 'Page not found'", async () => {
    await show("does-not-exist");
    expect(await screen.findByRole("heading", { level: 1, name: "Page not found" })).toBeDefined();
  });
});
