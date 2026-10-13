// SPDX-License-Identifier: AGPL-3.0-or-later
// Renders one plugin widget (M0S-E06-06): only if the plugin is in the build-time registry and enabled
// (GET /plugins), inside a WidgetFrame, a Suspense boundary and an error boundary. Anything else shows
// the "Widget unavailable" card instead of breaking the dashboard.
import type { PluginWebModule } from "@hearthos/sdk-ts";
import { Icon, WidgetFrame } from "@hearthos/ui";
import { Component, Suspense, use, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { ensurePluginLocales, pluginModulePromise } from "./load";
import { pluginRegistry } from "./registry.gen";

export type PluginLoaders = Record<string, () => Promise<{ default: PluginWebModule }>>;

export interface PluginWidgetProps {
  pluginId: string;
  widgetId: string;
  instanceId: string;
  size: { w: number; h: number };
  config?: Record<string, unknown>;
  /** Shown as the frame's heading; the dashboard passes the manifest's translated title. */
  title?: string;
  /** Enabled plugin ids from GET /plugins. */
  enabled: ReadonlySet<string>;
  loaders?: PluginLoaders;
}

export function PluginWidget({ loaders = pluginRegistry, enabled, ...props }: PluginWidgetProps) {
  const loader = loaders[props.pluginId];
  if (!loader || !enabled.has(props.pluginId)) return <WidgetUnavailable />;
  return (
    <WidgetErrorBoundary>
      <Suspense fallback={<WidgetFrame title={props.title ?? props.widgetId} />}>
        <LoadedWidget loader={loader} {...props} />
      </Suspense>
    </WidgetErrorBoundary>
  );
}

function LoadedWidget({
  loader,
  pluginId,
  widgetId,
  instanceId,
  size,
  config = {},
  title,
}: Omit<PluginWidgetProps, "enabled" | "loaders"> & { loader: PluginLoaders[string] }) {
  const { i18n } = useTranslation();
  const module = use(pluginModulePromise(loader));
  ensurePluginLocales(i18n, pluginId, module);
  const Widget = module.widgets[widgetId];
  if (!Widget) return <WidgetUnavailable />;
  return (
    <WidgetFrame title={title ?? widgetId}>
      <Widget instanceId={instanceId} pluginId={pluginId} size={size} config={config} />
    </WidgetFrame>
  );
}

export function WidgetUnavailable() {
  const { t } = useTranslation();
  return (
    <WidgetFrame title={t("widget.unavailable")}>
      <p className="flex items-center gap-2 text-muted-foreground">
        <Icon name="widget.unavailable" />
        {t("widget.unavailable_hint")}
      </p>
    </WidgetFrame>
  );
}

class WidgetErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? <WidgetUnavailable /> : this.props.children;
  }
}
