// SPDX-License-Identifier: AGPL-3.0-or-later
import { Outlet, createRootRouteWithContext, redirect } from "@tanstack/react-router";

import type { RouterContext } from "../router";
import { setupRequired } from "../setup";
import { NotFound } from "../shell/NotFound";

export const Route = createRootRouteWithContext<RouterContext>()({
  // A fresh install has no account yet: every page leads to the setup wizard (M1S-E03-02, ADR 0017).
  beforeLoad: async ({ context, location }) => {
    if (location.pathname !== "/setup" && (await setupRequired(context.queryClient))) throw redirect({ to: "/setup" });
  },
  component: Outlet,
  notFoundComponent: NotFound,
});
