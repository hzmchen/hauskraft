// SPDX-License-Identifier: AGPL-3.0-or-later
import { createMemoryHistory, createRouter } from "@tanstack/react-router";

import { routeTree } from "./routeTree.gen";

export interface RouterOptions {
  /** Start at this path with in-memory history (tests); the browser's location otherwise. */
  initialPath?: string;
}

export function createAppRouter(options: RouterOptions = {}) {
  return createRouter({
    routeTree,
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
