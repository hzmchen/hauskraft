// SPDX-License-Identifier: AGPL-3.0-or-later
// The Today dashboard (M0S-E08-06): the user's layout on a 12-column grid. Edit layout enables drag and
// resize; Done editing saves with PUT /dashboard/today. Below 768 px widgets stack in one column.
import {
  dashboardGetOptions,
  dashboardGetQueryKey,
  dashboardPutMutation,
  type DashboardCell,
  type PluginOut,
} from "@hearthos/sdk-ts";
import { Button } from "@hearthos/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { GridLayout, useContainerWidth } from "react-grid-layout";
import { useTranslation } from "react-i18next";

import { PluginWidget } from "../plugins/PluginWidget";
import { useWebPlugins } from "../plugins/usePlugins";
import { labelKey } from "../shell/nav/model";
import { useIsWide } from "../shell/nav/NavRenderer";
import {
  COLUMNS,
  fromGridLayout,
  readGridMetrics,
  stackOrder,
  toGridLayout,
  type GridMetrics,
  type MinSizes,
} from "./layout";

const PATH = { path: { dashboard_id: "today" } };

interface WidgetContribution {
  id: string;
  title?: string;
  min_size?: { w: number; h: number };
}

function widgetsOf(plugin: PluginOut): WidgetContribution[] {
  const widgets = (plugin.contributes as { widgets?: unknown }).widgets;
  return Array.isArray(widgets) ? (widgets as WidgetContribution[]) : [];
}

export function TodayDashboard() {
  const { t } = useTranslation();
  const wide = useIsWide();
  const queryClient = useQueryClient();
  const { data } = useQuery(dashboardGetOptions(PATH));
  const { plugins, enabled } = useWebPlugins();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<DashboardCell[] | null>(null);
  const save = useMutation({
    ...dashboardPutMutation(),
    onSuccess: (saved) => queryClient.setQueryData(dashboardGetQueryKey(PATH), saved),
  });
  const cells = draft ?? data?.layout ?? [];

  const { titles, minSizes } = useMemo(() => {
    const titleMap: Record<string, string> = {};
    const mins: MinSizes = {};
    for (const plugin of plugins) {
      for (const widget of widgetsOf(plugin)) {
        const key = `${plugin.id}/${widget.id}`;
        titleMap[key] = labelKey(widget.title, widget.id);
        if (widget.min_size) mins[key] = widget.min_size;
      }
    }
    return { titles: titleMap, minSizes: mins };
  }, [plugins]);

  async function toggleEditing() {
    if (editing) {
      await save.mutateAsync({ ...PATH, body: { layout: cells } });
      setDraft(null);
    }
    setEditing(!editing);
  }

  const renderCell = (cell: DashboardCell) => {
    const titleKey = titles[`${cell.plugin_id}/${cell.widget_id}`];
    return (
      <PluginWidget
        pluginId={cell.plugin_id}
        widgetId={cell.widget_id}
        instanceId={cell.i}
        size={{ w: cell.w, h: cell.h }}
        enabled={enabled}
        {...(titleKey ? { title: t(titleKey) } : {})}
      />
    );
  };

  return (
    <div className="flex flex-col gap-density">
      <div className="flex items-center justify-between gap-density">
        <h1 className="text-2xl font-bold">{t("nav.today")}</h1>
        {wide ? (
          <Button
            variant={editing ? "default" : "outline"}
            disabled={save.isPending}
            onClick={() => void toggleEditing()}
          >
            {editing ? t("dashboard.done_editing") : t("dashboard.edit_layout")}
          </Button>
        ) : null}
      </div>
      {wide ? (
        <DashboardGrid
          cells={cells}
          minSizes={minSizes}
          editing={editing}
          onChange={setDraft}
          renderCell={renderCell}
        />
      ) : (
        <div className="flex flex-col gap-density">
          {stackOrder(cells).map((cell) => (
            <div key={cell.i}>{renderCell(cell)}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function useGridMetrics(): GridMetrics {
  const [metrics, setMetrics] = useState(() => readGridMetrics(document.body));
  useEffect(() => {
    // Re-measure when the theme (or its density) changes: the shell updates these attributes.
    const observer = new MutationObserver(() => setMetrics(readGridMetrics(document.body)));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-hearth-theme", "data-hearth-density"],
    });
    return () => observer.disconnect();
  }, []);
  return metrics;
}

function DashboardGrid({
  cells,
  minSizes,
  editing,
  onChange,
  renderCell,
}: {
  cells: DashboardCell[];
  minSizes: MinSizes;
  editing: boolean;
  onChange: (cells: DashboardCell[]) => void;
  renderCell: (cell: DashboardCell) => React.ReactNode;
}) {
  const { width, containerRef, mounted } = useContainerWidth();
  const { rowHeight, gap } = useGridMetrics();
  return (
    <div ref={containerRef} data-editing={editing || undefined}>
      {mounted ? (
        <GridLayout
          width={width}
          layout={toGridLayout(cells, minSizes)}
          gridConfig={{ cols: COLUMNS, rowHeight, margin: [gap, gap], containerPadding: [0, 0] }}
          dragConfig={{ enabled: editing }}
          resizeConfig={{ enabled: editing }}
          onLayoutChange={(layout) => {
            if (editing) onChange(fromGridLayout(layout, cells));
          }}
        >
          {cells.map((cell) => (
            <div key={cell.i}>{renderCell(cell)}</div>
          ))}
        </GridLayout>
      ) : null}
    </div>
  );
}
