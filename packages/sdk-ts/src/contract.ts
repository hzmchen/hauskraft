// SPDX-License-Identifier: MIT
// What a plugin's web package gives the shell (spec §5, M0S-E06-05). UI primitives come from @hauskraft/ui.
import type { QueryClient } from "@tanstack/react-query";
import type { ComponentType } from "react";

export type WidgetProps = {
  instanceId: string;
  pluginId: string;
  size: { w: number; h: number };
  config: Record<string, unknown>;
};

export type PageProps = { pluginId: string };

export type PluginWebModule = {
  widgets: Record<string, ComponentType<WidgetProps>>;
  pages: Record<string, ComponentType<PageProps>>;
  /** i18n namespace per language; both languages are required. */
  locales: Record<"en" | "de", Record<string, unknown>>;
  /** Default SVGs for icon names the plugin introduces. */
  icons?: Record<string, string>;
  /**
   * Optional: load the data the plugin's widgets and pages show by default before they render, so they appear
   * complete at once instead of filling in. Called by the shell's Today and plugin-page routes each time one is opened, so load current data rather
   * reuse the cache; failures are ignored.
   */
  prefetch?: (queryClient: QueryClient) => Promise<unknown>;
};

/** Identity helper that type-checks a plugin's web module. */
export function definePluginWeb(module: PluginWebModule): PluginWebModule {
  return module;
}
