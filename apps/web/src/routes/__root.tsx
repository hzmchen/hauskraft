// SPDX-License-Identifier: AGPL-3.0-or-later
import { Outlet, createRootRouteWithContext } from "@tanstack/react-router";

import type { RouterContext } from "../router";
import { NotFound } from "../shell/NotFound";

export const Route = createRootRouteWithContext<RouterContext>()({
  component: Outlet,
  notFoundComponent: NotFound,
});
