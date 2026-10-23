// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { useEffect } from "react";
import { I18nextProvider } from "react-i18next";

import type { AppRouter } from "./router";
import { Toaster } from "@hauskraft/ui";

import { watchForEndedSessions } from "./session";
import { ColorModeProvider, useColorMode } from "./shell/ColorMode";
import { ThemeRuntime } from "./shell/ThemeRuntime";

export function App({ router, queryClient }: { router: AppRouter; queryClient: QueryClient }) {
  useEffect(
    () =>
      watchForEndedSessions(queryClient, () => {
        const redirect = router.state.location.href;
        void router.navigate({ to: "/login", search: { redirect, reason: "expired" } });
      }),
    [router, queryClient],
  );
  return (
    <I18nextProvider i18n={router.options.context.i18n}>
      <ColorModeProvider>
        <QueryClientProvider client={queryClient}>
          <ThemeRuntime>
            <RouterProvider router={router} />
            <ShellToaster />
          </ThemeRuntime>
        </QueryClientProvider>
      </ColorModeProvider>
    </I18nextProvider>
  );
}

/** One toast area for the shell and plugins, in this device's colour mode. */
function ShellToaster() {
  const { mode } = useColorMode();
  return <Toaster theme={mode} />;
}
