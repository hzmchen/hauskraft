// SPDX-License-Identifier: MIT
// Story gate: tests tagged with a red story are expected to fail (test.fail), so the suite stays usable
// while work is in progress. If a red story's test passes, Playwright reports it as a failure, which
// tells you to flip the story to "green" in tests/story-status.json. Set HEARTHOS_TDD_RAW=1 to see
// the real failures while you work on a story.
import { test as base, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

type Status = { status: "red" | "green"; acceptance: "suite" | "in-story" };

const here = dirname(fileURLToPath(import.meta.url));
const registry: Record<string, Status> = JSON.parse(
  readFileSync(resolve(here, "..", "..", "story-status.json"), "utf-8"),
).stories;
const RAW = process.env.HEARTHOS_TDD_RAW === "1";

/** `story("M0S-E09-01", "M0S-E11-03")` -> tag list for `test(title, { tag }, fn)`. */
export function story(...ids: string[]): { tag: string[] } {
  for (const id of ids) {
    if (!registry[id]) throw new Error(`Unknown story id ${id} (not in tests/story-status.json)`);
  }
  return { tag: ids.map((id) => `@${id}`) };
}

export const test = base.extend<{ storyGate: void }>({
  storyGate: [
    async ({}, use, testInfo) => {
      const ids = testInfo.tags.map((t) => t.replace(/^@/, "")).filter((t) => t.startsWith("M0S-"));
      if (ids.length === 0) throw new Error(`${testInfo.title}: every e2e test needs story(...) tags`);
      const red = ids.filter((id) => registry[id]?.status === "red");
      if (red.length && !RAW) testInfo.fail(true, `RED: ${red.join(", ")} not implemented yet`);
      await use();
    },
    { auto: true },
  ],
});

export { expect };
