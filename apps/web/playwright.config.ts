// SPDX-License-Identifier: AGPL-3.0-or-later
// Web-shell checks against a running stack (M0S-E11-01). The spec-owned suites live in tests/e2e.
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  workers: 1,
  timeout: 120_000,
  reporter: [["list"]],
  outputDir: "test-results",
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
