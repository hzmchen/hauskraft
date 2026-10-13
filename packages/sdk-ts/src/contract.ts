// SPDX-License-Identifier: MIT
// What a plugin's web package gives the shell (spec §5, M0S-E06-05). UI primitives come from @hearthos/ui.
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
};

/** Identity helper that type-checks a plugin's web module. */
export function definePluginWeb(module: PluginWebModule): PluginWebModule {
  return module;
}
