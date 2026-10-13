// SPDX-License-Identifier: AGPL-3.0-or-later
import type { QueryClient } from "@tanstack/react-query";
import { createMemoryHistory, createRouter } from "@tanstack/react-router";

import { routeTree } from "./routeTree.gen";

export interface RouterContext {
  queryClient: QueryClient;
}

export interface RouterOptions {
  queryClient: QueryClient;
  /** Start at this path with in-memory history (tests); the browser's location otherwise. */
  initialPath?: string;
}

export function createAppRouter(options: RouterOptions) {
  return createRouter({
    routeTree,
    context: { queryClient: options.queryClient },
    defaultPreload: "intent",
    scrollRestoration: true,
    ...(options.initialPath ? { history: createMemoryHistory({ initialEntries: [options.initialPath] }) } : {}),
  });
}

export type AppRouter = ReturnType<typeof createAppRouter>;

declare module "@tanstack/react-router" {
  interface Register {
    router: AppRouter;
  }
}
