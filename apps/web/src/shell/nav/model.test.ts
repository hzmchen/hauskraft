// SPDX-License-Identifier: AGPL-3.0-or-later
import type { PluginOut } from "@hearthos/sdk-ts";
import { describe, expect, it } from "vitest";

import { buildNavModel } from "./model";

const tasks: PluginOut = {
  id: "org.hearthos.tasks",
  name: "Tasks",
  version: "0.1.0",
  kind: "inprocess",
  type: ["domain", "widget"],
  enabled: true,
  load_error: null,
  contributes: {
    pages: [
      {
        id: "tasks",
        title: "i18n:tasks:page.title",
        component: "TasksPage",
        nav: true,
        icon: "nav.tasks",
        nav_order: 20,
      },
      { id: "tasks-archive", title: "i18n:tasks:archive.title", component: "Archive", nav: false },
    ],
  },
};

describe("buildNavModel", () => {
  it("orders Today, plugin pages, Activity, Settings", () => {
    expect(buildNavModel([tasks]).map((i) => [i.id, i.href, i.order])).toEqual([
      ["today", "/today", 10],
      ["org.hearthos.tasks/tasks", "/p/tasks", 20],
      ["activity", "/activity", 90],
      ["settings", "/settings", 100],
    ]);
  });

  it("takes label keys and icons from the manifest", () => {
    const item = buildNavModel([tasks])[1]!;
    expect(item).toMatchObject({ labelKey: "tasks:page.title", icon: "nav.tasks" });
  });

  it("leaves out pages that are not in the navigation", () => {
    expect(buildNavModel([tasks]).some((i) => i.href === "/p/tasks-archive")).toBe(false);
  });

  it("keeps the core items when no plugin contributes pages", () => {
    expect(buildNavModel([]).map((i) => i.id)).toEqual(["today", "activity", "settings"]);
  });

  it("is stable for equal orders (by id)", () => {
    const other = {
      ...tasks,
      id: "org.example.alpha",
      contributes: { pages: [{ id: "alpha", title: "x", component: "A", nav: true, nav_order: 20 }] },
    };
    expect(buildNavModel([tasks, other]).map((i) => i.href)).toEqual([
      "/today",
      "/p/alpha",
      "/p/tasks",
      "/activity",
      "/settings",
    ]);
  });
});
