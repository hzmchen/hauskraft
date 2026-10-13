// SPDX-License-Identifier: MIT
import type { QueryClient } from "@tanstack/react-query";
import type { ComponentType } from "react";
import { describe, expectTypeOf, it } from "vitest";

import { definePluginWeb, type PageProps, type PluginWebModule, type WidgetProps } from "./index";

describe("widget and page contract", () => {
  it("WidgetProps has the documented shape", () => {
    expectTypeOf<WidgetProps>().toEqualTypeOf<{
      instanceId: string;
      pluginId: string;
      size: { w: number; h: number };
      config: Record<string, unknown>;
    }>();
  });

  it("PageProps has the documented shape", () => {
    expectTypeOf<PageProps>().toEqualTypeOf<{ pluginId: string }>();
  });

  it("PluginWebModule has widgets, pages, locales and optional icons", () => {
    expectTypeOf<PluginWebModule["widgets"]>().toEqualTypeOf<Record<string, ComponentType<WidgetProps>>>();
    expectTypeOf<PluginWebModule["pages"]>().toEqualTypeOf<Record<string, ComponentType<PageProps>>>();
    expectTypeOf<PluginWebModule["locales"]>().toEqualTypeOf<Record<"en" | "de", Record<string, unknown>>>();
    expectTypeOf<PluginWebModule["icons"]>().toEqualTypeOf<Record<string, string> | undefined>();
    expectTypeOf<PluginWebModule["prefetch"]>().toEqualTypeOf<
      ((queryClient: QueryClient) => Promise<unknown>) | undefined
    >();
  });

  it("definePluginWeb returns the module unchanged and rejects missing locales", () => {
    const module = { widgets: {}, pages: {}, locales: { en: {}, de: {} } };
    expectTypeOf(definePluginWeb(module)).toEqualTypeOf<PluginWebModule>();
    // @ts-expect-error: German strings are required
    definePluginWeb({ widgets: {}, pages: {}, locales: { en: {} } });
  });
});
