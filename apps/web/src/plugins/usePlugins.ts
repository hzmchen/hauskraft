// SPDX-License-Identifier: AGPL-3.0-or-later
import { pluginsListOptions, type PluginOut } from "@hearthos/sdk-ts";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { pluginRegistry } from "./registry.gen";

/** Plugins that are enabled (GET /plugins) and have web code in this build. */
export function useWebPlugins(): { plugins: PluginOut[]; enabled: ReadonlySet<string>; isPending: boolean } {
  const { data, isPending } = useQuery(pluginsListOptions());
  return useMemo(() => {
    const plugins = (data ?? []).filter((p) => p.enabled && !p.load_error && p.id in pluginRegistry);
    return { plugins, enabled: new Set(plugins.map((p) => p.id)), isPending };
  }, [data, isPending]);
}
