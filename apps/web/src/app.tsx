// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { I18nextProvider } from "react-i18next";

import type { AppRouter } from "./router";
import { ColorModeProvider } from "./shell/ColorMode";
import { ThemeRuntime } from "./shell/ThemeRuntime";

export function App({ router, queryClient }: { router: AppRouter; queryClient: QueryClient }) {
  return (
    <I18nextProvider i18n={router.options.context.i18n}>
      <ColorModeProvider>
        <QueryClientProvider client={queryClient}>
          <ThemeRuntime>
            <RouterProvider router={router} />
          </ThemeRuntime>
        </QueryClientProvider>
      </ColorModeProvider>
    </I18nextProvider>
  );
}
