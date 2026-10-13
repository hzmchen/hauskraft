// SPDX-License-Identifier: MIT
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { playwright } from "@vitest/browser-playwright";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { fs: { allow: ["../.."] } },
  test: {
    globals: true, // lets Testing Library clean up after each test
    projects: [
      {
        extends: true,
        test: {
          name: "unit",
          environment: "jsdom",
          include: ["src/**/*.test.{ts,tsx}"],
          exclude: ["src/**/*.browser.test.{ts,tsx}"],
        },
      },
      {
        extends: true,
        test: {
          name: "browser",
          include: ["src/**/*.browser.test.{ts,tsx}"],
          browser: { enabled: true, headless: true, provider: playwright(), instances: [{ browser: "chromium" }] },
        },
      },
    ],
  },
});
