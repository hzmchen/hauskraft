// SPDX-License-Identifier: AGPL-3.0-or-later
import type { QueryClient } from "@tanstack/react-query";
import { createMemoryHistory, createRouter } from "@tanstack/react-router";
import type { i18n as I18n } from "i18next";

import { routeTree } from "./routeTree.gen";

export interface RouterContext {
  queryClient: QueryClient;
  i18n: I18n;
}

export interface RouterOptions extends RouterContext {
  /** Start at this path with in-memory history (tests); the browser's location otherwise. */
  initialPath?: string;
}

export function createAppRouter({ queryClient, i18n, initialPath }: RouterOptions) {
  return createRouter({
    routeTree,
    context: { queryClient, i18n },
    defaultPreload: "intent",
    scrollRestoration: true,
    ...(initialPath ? { history: createMemoryHistory({ initialEntries: [initialPath] }) } : {}),
  });
}

export type AppRouter = ReturnType<typeof createAppRouter>;

declare module "@tanstack/react-router" {
  interface Register {
    router: AppRouter;
  }
}
