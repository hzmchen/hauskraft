// SPDX-License-Identifier: AGPL-3.0-or-later
import { Outlet, createRootRoute } from "@tanstack/react-router";

export const Route = createRootRoute({ component: Root });

function Root() {
  return (
    <main id="content">
      <Outlet />
    </main>
  );
}
