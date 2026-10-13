// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app";
import { createI18n } from "./i18n";
import { createAppRouter } from "./router";
import "./styles.css";

const root = document.getElementById("root");
if (!root) throw new Error("#root missing from index.html");

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 10_000 } } });
const router = createAppRouter({ queryClient, i18n: createI18n() });

createRoot(root).render(
  <StrictMode>
    <App router={router} queryClient={queryClient} />
  </StrictMode>,
);
