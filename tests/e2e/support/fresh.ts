// SPDX-License-Identifier: MIT
// The unseeded "fresh" stack for first-run tests (M1S-E01-01). Specs that use it skip themselves unless
// HAUSKRAFT_FRESH_BASE_URL is set; CI always sets it (M1S-E01-02).
import { execSync } from "node:child_process";
import { request } from "@playwright/test";

export const FRESH_URL = process.env.HAUSKRAFT_FRESH_BASE_URL ?? "";
export const FRESH_ENABLED = FRESH_URL !== "";
const RESET_CMD = process.env.HAUSKRAFT_FRESH_RESET_CMD ?? "";

async function setupRequired(): Promise<boolean> {
  const ctx = await request.newContext({ baseURL: `${FRESH_URL}/api/v1/` });
  try {
    const r = await ctx.get("setup");
    if (!r.ok()) throw new Error(`RED (M1S-E03-01): GET /setup on the fresh stack answered ${r.status()}`);
    return (await r.json()).required === true;
  } finally {
    await ctx.dispose();
  }
}

/** Leave the fresh stack empty, running HAUSKRAFT_FRESH_RESET_CMD if it was already set up. */
export async function resetFreshStack(): Promise<void> {
  if (await setupRequired()) return;
  if (!RESET_CMD) throw new Error("the fresh stack is already set up; set HAUSKRAFT_FRESH_RESET_CMD or run `just fresh-reset`");
  execSync(RESET_CMD, { stdio: "inherit", timeout: 600_000 });
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    if (await setupRequired().catch(() => false)) return;
    await new Promise((resolve) => setTimeout(resolve, 2_000));
  }
  throw new Error("the fresh stack did not come back empty after HAUSKRAFT_FRESH_RESET_CMD");
}
