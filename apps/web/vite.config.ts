// SPDX-License-Identifier: AGPL-3.0-or-later
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The router plugin must run before the React plugin (it generates src/routeTree.gen.ts and splits routes).
export default defineConfig({
  plugins: [tanstackRouter({ target: "react", autoCodeSplitting: true }), react(), tailwindcss()],
  server: {
    // `pnpm --filter web dev` talks to a local API (`uvicorn … --port 8000`); same origin, so cookies work.
    // The API checks Origin on writes: add the dev URL to HEARTHOS_ALLOWED_ORIGINS (e.g. http://localhost:5173).
    proxy: { "/api": process.env.HEARTHOS_API_URL ?? "http://127.0.0.1:8000" },
  },
});
