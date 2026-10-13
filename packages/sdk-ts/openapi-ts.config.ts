// SPDX-License-Identifier: MIT
// Generates src/client/ from the committed OpenAPI contract (M0S-E06-05). Run with `just gen`.
import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "../schemas/openapi/core-api.openapi.json",
  output: { path: "src/client" },
  plugins: [
    { name: "@hey-api/client-fetch", runtimeConfigPath: "./src/runtime-config" },
    "@hey-api/typescript",
    "@hey-api/sdk",
    "@tanstack/react-query",
  ],
});
