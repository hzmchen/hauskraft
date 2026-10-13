// SPDX-License-Identifier: AGPL-3.0-or-later
// Renderer contract (E08-05, E13-05): every renderer shows the same items, in model order, with the same
// names and links, inside a navigation landmark named "Main". Only presentation may differ.
import { RouterProvider, createMemoryHistory, createRootRoute, createRouter } from "@tanstack/react-router";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentType } from "react";
import { I18nextProvider } from "react-i18next";
import { describe, expect, it } from "vitest";

import { createI18n } from "../../i18n";
import { DrawerNav } from "./DrawerNav";
import type { NavItem, NavRendererProps } from "./model";
import { SidebarNav } from "./SidebarNav";

const MODEL: NavItem[] = [
  { id: "today", labelKey: "nav.today", icon: "nav.today", href: "/today", order: 10 },
  { id: "x/tasks", labelKey: "test:tasks", icon: "nav.tasks", href: "/p/tasks", order: 20 },
  { id: "activity", labelKey: "nav.activity", icon: "nav.activity", href: "/activity", order: 90 },
  { id: "settings", labelKey: "nav.settings", icon: "nav.settings", href: "/settings", order: 100 },
];

export const RENDERERS: [string, ComponentType<NavRendererProps>][] = [
  ["sidebar", SidebarNav],
  ["drawer", DrawerNav],
];

async function show(Renderer: ComponentType<NavRendererProps>) {
  const i18n = createI18n({ lng: "en" });
  i18n.addResourceBundle("en", "test", { tasks: "Tasks" });
  const router = createRouter({
    routeTree: createRootRoute({ component: () => <Renderer items={MODEL} /> }),
    history: createMemoryHistory({ initialEntries: ["/today"] }),
  });
  await act(async () => {
    render(
      <I18nextProvider i18n={i18n}>
        <RouterProvider router={router} />
      </I18nextProvider>,
    );
  });
}

async function openIfNeeded() {
  const opener = screen.queryByRole("button", { name: "Open menu" });
  if (opener) await userEvent.click(opener);
}

describe.each(RENDERERS)("%s renderer", (style, Renderer) => {
  it("renders every item in model order with the same names and links", async () => {
    await show(Renderer);
    await openIfNeeded();
    const nav = await screen.findByRole("navigation", { name: "Main" });
    const links = within(nav).getAllByRole("link");
    expect(links.map((l) => l.textContent?.trim())).toEqual(["Today", "Tasks", "Activity", "Settings"]);
    expect(links.map((l) => l.getAttribute("href"))).toEqual(["/today", "/p/tasks", "/activity", "/settings"]);
    expect(nav.getAttribute("data-nav-style")).toBe(style);
  });

  it("marks the current page", async () => {
    await show(Renderer);
    await openIfNeeded();
    const nav = await screen.findByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "Today" }).getAttribute("aria-current")).toBe("page");
  });
});
