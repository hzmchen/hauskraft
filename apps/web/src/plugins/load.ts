// SPDX-License-Identifier: AGPL-3.0-or-later
import type { PluginWebModule } from "@hearthos/sdk-ts";
import type { i18n as I18n } from "i18next";

import { addPluginLocales, LANGUAGES } from "../i18n";

/** A plugin's i18n namespace is the last segment of its id: org.hearthos.tasks → "tasks". */
export function pluginNamespace(pluginId: string): string {
  return pluginId.slice(pluginId.lastIndexOf(".") + 1);
}

type Loader = () => Promise<{ default: PluginWebModule }>;

// One promise per loader function. React's use() needs the very same promise on every render, and the
// registry's loaders are stable, so they make the key (not the i18n object, which hooks may re-wrap).
const modules = new WeakMap<Loader, Promise<PluginWebModule>>();

/** Register the plugin's strings once per i18n instance (idempotent). */
export function ensurePluginLocales(i18n: I18n, pluginId: string, module: PluginWebModule): void {
  const namespace = pluginNamespace(pluginId);
  if (LANGUAGES.every((lng) => i18n.hasResourceBundle(lng, namespace))) return;
  addPluginLocales(i18n, namespace, module.locales);
}

/** The cached module promise for `loader`; React's use() needs the same promise on every render. */
export function pluginModulePromise(loader: Loader): Promise<PluginWebModule> {
  let promise = modules.get(loader);
  if (!promise) {
    const pending = loader().then(({ default: module }) => {
      // React's thenable protocol: with status and value set, use() returns at once instead of suspending
      // for a tick on an already-loaded module (which would flash the widget's loading frame).
      Object.assign(pending, { status: "fulfilled", value: module });
      return module;
    });
    promise = pending;
    modules.set(loader, promise);
  }
  return promise;
}

/** Load a plugin's web module (once) and make sure its strings are registered with `i18n`. */
export async function loadPluginModule(pluginId: string, loader: Loader, i18n: I18n): Promise<PluginWebModule> {
  const module = await pluginModulePromise(loader);
  ensurePluginLocales(i18n, pluginId, module);
  return module;
}
