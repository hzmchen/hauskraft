// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import type { i18n as I18n } from "i18next";
import { useState } from "react";
import { I18nextProvider } from "react-i18next";

import { createI18n } from "./i18n";
import type { AppRouter } from "./router";
import { ColorModeProvider } from "./shell/ColorMode";

export function App({ router, i18n }: { router: AppRouter; i18n?: I18n }) {
  const [queryClient] = useState(() => new QueryClient({ defaultOptions: { queries: { staleTime: 10_000 } } }));
  const [translations] = useState(() => i18n ?? createI18n());
  return (
    <I18nextProvider i18n={translations}>
      <ColorModeProvider>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </ColorModeProvider>
    </I18nextProvider>
  );
}
