// SPDX-License-Identifier: AGPL-3.0-or-later
import type { PluginWebModule } from "@hearthos/sdk-ts";
import type { i18n as I18n } from "i18next";

import { addPluginLocales } from "../i18n";

/** A plugin's i18n namespace is the last segment of its id: org.hearthos.tasks → "tasks". */
export function pluginNamespace(pluginId: string): string {
  return pluginId.slice(pluginId.lastIndexOf(".") + 1);
}

const loaded = new WeakMap<I18n, Map<string, Promise<PluginWebModule>>>();

/** Load a plugin's web module once per i18n instance and register its strings. */
export function loadPluginModule(
  pluginId: string,
  loader: () => Promise<{ default: PluginWebModule }>,
  i18n: I18n,
): Promise<PluginWebModule> {
  let cache = loaded.get(i18n);
  if (!cache) loaded.set(i18n, (cache = new Map()));
  let promise = cache.get(pluginId);
  if (!promise) {
    promise = loader().then(({ default: module }) => {
      addPluginLocales(i18n, pluginNamespace(pluginId), module.locales);
      return module;
    });
    cache.set(pluginId, promise);
  }
  return promise;
}
