// SPDX-License-Identifier: MIT
// Spec-owned end-to-end acceptance tests. Run against a started stack:
//   docker compose -f compose.yaml -f deploy/compose/compose.test.yaml up --wait
//   pnpm --filter @hauskraft/acceptance-e2e test
import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.HAUSKRAFT_BASE_URL ?? "http://localhost:8080";

export default defineConfig({
  testDir: ".",
  testMatch: /.*\.spec\.ts$/,
  fullyParallel: false,
  workers: 1, // tests share one household; the demo script is serial by design
  retries: 0,
  timeout: 120_000,
  expect: { timeout: 10_000 },
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  outputDir: "test-results",
  snapshotPathTemplate: "{testDir}/__screenshots__/{testFilePath}/{arg}{ext}",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    locale: "en-GB",
    timezoneId: "Europe/Berlin",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } },
  ],
});
