// SPDX-License-Identifier: AGPL-3.0-or-later
import { afterEach, describe, expect, it, vi } from "vitest";

import { fromGridLayout, readGridMetrics, stackOrder, toGridLayout } from "./layout";

const cells = [
  { i: "a", plugin_id: "org.hearthos.tasks", widget_id: "tasks.list", x: 4, y: 0, w: 4, h: 6 },
  { i: "b", plugin_id: "org.example.x", widget_id: "x.y", x: 0, y: 0, w: 4, h: 3 },
];

afterEach(() => vi.restoreAllMocks());

describe("layout mapping", () => {
  it("turns API cells into grid items with the manifest's minimum size", () => {
    const items = toGridLayout(cells, { "org.hearthos.tasks/tasks.list": { w: 3, h: 4 } });
    expect(items[0]).toEqual({ i: "a", x: 4, y: 0, w: 4, h: 6, minW: 3, minH: 4 });
    expect(items[1]).toEqual({ i: "b", x: 0, y: 0, w: 4, h: 3 });
  });

  it("maps a moved grid back to API cells, keeping plugin and widget", () => {
    const moved = [
      { i: "a", x: 0, y: 3, w: 6, h: 6 },
      { i: "b", x: 0, y: 0, w: 12, h: 3 },
    ];
    expect(fromGridLayout(moved, cells)).toEqual([
      { i: "a", plugin_id: "org.hearthos.tasks", widget_id: "tasks.list", x: 0, y: 3, w: 6, h: 6 },
      { i: "b", plugin_id: "org.example.x", widget_id: "x.y", x: 0, y: 0, w: 12, h: 3 },
    ]);
  });

  it("stacks narrow screens top-to-bottom, left-to-right", () => {
    expect(stackOrder(cells).map((c) => c.i)).toEqual(["b", "a"]);
  });
});

describe("grid metrics", () => {
  it("reads row height and gutter from the theme's CSS variables", () => {
    vi.spyOn(window, "getComputedStyle").mockImplementation(
      (el) =>
        ({
          height: (el as HTMLElement).style.height === "var(--hearth-grid-row)" ? "34px" : "0px",
          width: (el as HTMLElement).style.width === "var(--hearth-grid-gap)" ? "13.6px" : "0px",
        }) as CSSStyleDeclaration,
    );
    expect(readGridMetrics(document.body)).toEqual({ rowHeight: 34, gap: 13.6 });
  });

  it("falls back to the Default theme's metrics when the variables are missing", () => {
    vi.spyOn(window, "getComputedStyle").mockImplementation(
      () => ({ height: "0px", width: "0px" }) as CSSStyleDeclaration,
    );
    expect(readGridMetrics(document.body)).toEqual({ rowHeight: 40, gap: 16 });
  });
});
