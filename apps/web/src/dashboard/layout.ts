// SPDX-License-Identifier: AGPL-3.0-or-later
// Dashboard layout helpers (M0S-E08-06). The API stores cells {i, plugin_id, widget_id, x, y, w, h} on a
// 12-column grid; react-grid-layout works with {i, x, y, w, h, minW?, minH?}.
import type { DashboardCell } from "@hearthos/sdk-ts";

export const COLUMNS = 12;

export interface GridItem {
  i: string;
  x: number;
  y: number;
  w: number;
  h: number;
  minW?: number;
  minH?: number;
}

/** Minimum sizes from the manifests, keyed "<plugin_id>/<widget_id>". */
export type MinSizes = Record<string, { w: number; h: number }>;

export function toGridLayout(cells: DashboardCell[], minSizes: MinSizes = {}): GridItem[] {
  return cells.map(({ i, x, y, w, h, plugin_id, widget_id }) => {
    const min = minSizes[`${plugin_id}/${widget_id}`];
    return min ? { i, x, y, w, h, minW: min.w, minH: min.h } : { i, x, y, w, h };
  });
}

export function fromGridLayout(items: readonly GridItem[], cells: DashboardCell[]): DashboardCell[] {
  const byId = new Map(cells.map((cell) => [cell.i, cell]));
  return items.flatMap(({ i, x, y, w, h }) => {
    const cell = byId.get(i);
    return cell ? [{ i, plugin_id: cell.plugin_id, widget_id: cell.widget_id, x, y, w, h }] : [];
  });
}

/** Narrow screens show one column: top to bottom, then left to right. */
export function stackOrder(cells: DashboardCell[]): DashboardCell[] {
  return [...cells].sort((a, b) => a.y - b.y || a.x - b.x);
}

export interface GridMetrics {
  rowHeight: number;
  gap: number;
}

/** The Default theme's values (comfortable density, 4 px unit): rows 40 px, gutters 16 px. */
export const DEFAULT_METRICS: GridMetrics = { rowHeight: 40, gap: 16 };

/**
 * Row height and gutter come from the active theme (--hearth-grid-row, --hearth-grid-gap; density
 * scales both). They are calc() expressions, so a hidden probe lets the browser resolve them.
 */
export function readGridMetrics(root: HTMLElement): GridMetrics {
  const probe = document.createElement("div");
  probe.setAttribute("aria-hidden", "true");
  probe.style.position = "absolute";
  probe.style.visibility = "hidden";
  probe.style.height = "var(--hearth-grid-row)";
  probe.style.width = "var(--hearth-grid-gap)";
  root.append(probe);
  const style = window.getComputedStyle(probe);
  const rowHeight = parseFloat(style.height);
  const gap = parseFloat(style.width);
  probe.remove();
  return {
    rowHeight: rowHeight > 0 ? rowHeight : DEFAULT_METRICS.rowHeight,
    gap: gap > 0 ? gap : DEFAULT_METRICS.gap,
  };
}
