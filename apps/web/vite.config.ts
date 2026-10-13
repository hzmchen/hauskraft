// SPDX-License-Identifier: AGPL-3.0-or-later
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

import { writeRegistry } from "../../scripts/gen-plugin-registry.mjs";

/** Regenerate src/plugins/registry.gen.ts from the plugin manifests (M0S-E06-06). */
const pluginRegistry = (): Plugin => ({ name: "hearthos-plugin-registry", buildStart: () => void writeRegistry() });

// The router plugin must run before the React plugin (it generates src/routeTree.gen.ts and splits routes).
export default defineConfig({
  plugins: [pluginRegistry(), tanstackRouter({ target: "react", autoCodeSplitting: true }), react(), tailwindcss()],
  server: {
    // `pnpm --filter web dev` talks to a local API (`uvicorn … --port 8000`); same origin, so cookies work.
    // The API checks Origin on writes: add the dev URL to HEARTHOS_ALLOWED_ORIGINS (e.g. http://localhost:5173).
    proxy: { "/api": process.env.HEARTHOS_API_URL ?? "http://127.0.0.1:8000" },
  },
});
