// SPDX-License-Identifier: AGPL-3.0-or-later
// The one navigation model (M0S-E08-05, AGENTS.md rule 13). Every renderer gets these items; none may
// filter, reorder, rename or relabel them.
import type { PluginOut } from "@hauskraft/sdk-ts";

export interface NavItem {
  id: string;
  /** i18n key, e.g. "nav.today" or "tasks:page.title" for a plugin's own namespace. */
  labelKey: string;
  icon: string;
  href: string;
  order: number;
}

export interface NavRendererProps {
  items: NavItem[];
}

export interface PageContribution {
  id: string;
  title?: string;
  component?: string;
  nav?: boolean;
  icon?: string;
  nav_order?: number;
}

const CORE: NavItem[] = [
  { id: "today", labelKey: "nav.today", icon: "nav.today", href: "/today", order: 10 },
  { id: "activity", labelKey: "nav.activity", icon: "nav.activity", href: "/activity", order: 90 },
  { id: "settings", labelKey: "nav.settings", icon: "nav.settings", href: "/settings", order: 100 },
];

export function pluginPages(plugin: PluginOut): PageContribution[] {
  const pages = (plugin.contributes as { pages?: unknown }).pages;
  return Array.isArray(pages) ? (pages as PageContribution[]) : [];
}

/** "i18n:tasks:page.title" → "tasks:page.title" (namespace:key). */
export function labelKey(title: string | undefined, fallback: string): string {
  if (!title) return fallback;
  return title.startsWith("i18n:") ? title.slice("i18n:".length) : title;
}

export function buildNavModel(plugins: PluginOut[]): NavItem[] {
  const contributed = plugins.flatMap((plugin) =>
    pluginPages(plugin)
      .filter((page) => page.nav)
      .map((page) => ({
        id: `${plugin.id}/${page.id}`,
        labelKey: labelKey(page.title, page.id),
        icon: page.icon ?? "nav.today",
        href: `/p/${page.id}`,
        order: page.nav_order ?? 50,
      })),
  );
  return [...CORE, ...contributed].sort((a, b) => a.order - b.order || a.href.localeCompare(b.href));
}
