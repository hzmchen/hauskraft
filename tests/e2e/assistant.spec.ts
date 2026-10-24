// SPDX-License-Identifier: MIT
// M2S-E06/E07 on the demo stack with the fake model: the Assistant section in Settings, the side panel's behaviour,
// and function invariance of the panel and Settings → Assistant across themes (spec §10.2.2).
import AxeBuilder from "@axe-core/playwright";
import type { Locator, Page } from "@playwright/test";
import { Api, THEMES } from "./support/api";
import { expect, story, test } from "./support/stories";
import { assistant, goNav, htmlAttr, login, navItems, settingsNav, settingsSections, ui } from "./support/ui";

const THEME_IDS = [THEMES.default, THEMES.paper, THEMES.hackspace];
const MODES = ["light", "dark"] as const;
const VIEWPORTS = { wide: { width: 1280, height: 800 }, narrow: { width: 390, height: 844 } };

// Red stories fail fast instead of waiting for the 120 s test timeout on a missing element.
test.use({ actionTimeout: 15_000 });

let api: Api;
test.beforeAll(async () => {
  api = await Api.login("demo").catch(() => undefined as unknown as Api);
  await api?.configureAssistant().catch(() => undefined);
});
test.afterAll(async () => {
  await api?.configureAssistant().catch(() => undefined);
  await api?.setTheme(THEMES.default).catch(() => undefined);
  await api?.dispose();
});

test.describe("the Assistant section", () => {
  test("owners see it after Members", story("M2S-E07-01"), async ({ page }) => {
    await login(page, "demo");
    await goNav(page, "Settings");
    expect(await settingsSections(page)).toEqual(["Appearance", "Account", "Household", "Members", "Assistant"]);
    await settingsNav(page).getByRole("link", { name: "Assistant", exact: true }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Assistant" })).toBeVisible();
    for (const region of ["Endpoint", "Tools", "Usage"]) {
      await expect(page.getByRole("region", { name: region })).toBeVisible();
    }
  });

  test("adults are sent to Appearance", story("M2S-E07-01"), async ({ page }) => {
    await login(page, "alex");
    await page.goto("/settings/assistant");
    await expect(page).toHaveURL(/\/settings\/appearance$/);
  });
});

test.describe("the side panel", () => {
  test("there is no button without an endpoint", story("M2S-E06-01"), async ({ page }) => {
    await api.status("DELETE", "assistant/settings/chat");
    try {
      await login(page, "alex");
      await expect(ui.main(page)).toBeVisible();
      await expect(assistant.button(page)).toHaveCount(0);
    } finally {
      await api.configureAssistant();
    }
  });

  test("it opens beside the page and stays open on this device", story("M2S-E06-01"), async ({ page }) => {
    await login(page, "demo");
    const button = assistant.button(page);
    await expect(button).toHaveAttribute("aria-expanded", "false");
    await button.click();
    await expect(assistant.panel(page)).toBeVisible();
    await expect(button).toHaveAttribute("aria-expanded", "true");
    await expect(ui.addTask(page)).toBeVisible(); // the page stays usable on wide screens
    await page.reload();
    await expect(assistant.panel(page)).toBeVisible();
    await button.click();
    await expect(assistant.panel(page)).toBeHidden();
  });

  test("on narrow screens it covers the page and gives focus back", story("M2S-E06-01"), async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: VIEWPORTS.narrow });
    const page = await ctx.newPage();
    try {
      await login(page, "demo");
      await assistant.button(page).click();
      await expect(assistant.panel(page)).toBeVisible();
      await assistant.panel(page).getByRole("button", { name: "Close assistant" }).click();
      await expect(assistant.panel(page)).toBeHidden();
      await expect(assistant.button(page)).toBeFocused();
    } finally {
      await ctx.close();
    }
  });
});

const MASKED = /^(\s*)- (list "(Chats|Connection checks)"|log "Messages"|table "Usage by (day|member|model)")/;

/** Mask what legitimately differs between captures: the selected theme, chats, messages and usage numbers. */
function normalise(snapshot: string): string {
  const out: string[] = [];
  let maskDepth = -1;
  for (const line of snapshot.replace(/(radio "[^"]+") \[checked\]/g, "$1").split("\n")) {
    const depth = line.length - line.trimStart().length;
    if (maskDepth >= 0 && depth > maskDepth) continue;
    maskDepth = -1;
    out.push(line);
    const m = MASKED.exec(line);
    if (m) {
      maskDepth = m[1].length;
      out.push(`${m[1]}  - <masked>`);
    }
  }
  return out.join("\n");
}

const VIEWS: { name: string; path: string; root: (page: Page) => Locator; stories: string[] }[] = [
  { name: "Settings → Assistant", path: "/settings/assistant", root: ui.main, stories: ["M2S-E07-01", "M2S-E07-02", "M2S-E07-03"] },
  { name: "the side panel", path: "/today", root: assistant.panel, stories: ["M2S-E06-01", "M2S-E06-02", "M2S-E06-03"] },
];

test.describe("assistant views are function-invariant across themes", () => {
  for (const [vpName, viewport] of Object.entries(VIEWPORTS)) {
    for (const view of VIEWS) {
      test(`${view.name} @ ${vpName}`, story(...view.stories), async ({ browser }) => {
        let baseline: { tree: string; nav: string[] } | undefined;
        for (const themeId of THEME_IDS) {
          await api.setTheme(themeId);
          for (const mode of MODES) {
            const ctx = await browser.newContext({ viewport, colorScheme: mode });
            await ctx.addInitScript((m) => {
              try { localStorage.setItem("hauskraft.mode", m); } catch { /* storage blocked */ }
            }, mode);
            const page = await ctx.newPage();
            await login(page, "demo");
            await page.goto(view.path);
            await expect.poll(() => htmlAttr(page, "data-hauskraft-theme")).toBe(themeId);
            if (view.path === "/today" && !(await assistant.panel(page).isVisible())) await assistant.button(page).click();
            await view.root(page).waitFor();
            const got = { tree: normalise(await view.root(page).ariaSnapshot()), nav: await navItems(page) };
            if (!baseline) baseline = got;
            expect(got.nav, `${themeId}/${mode}: navigation items differ`).toEqual(baseline.nav);
            expect(got.tree, `${themeId}/${mode}: accessibility tree differs`).toBe(baseline.tree);
            const axe = await new AxeBuilder({ page }).analyze();
            const serious = axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
            expect(serious.map((v) => `${v.id}: ${v.help}`), `${themeId}/${mode}: axe violations`).toEqual([]);
            await ctx.close();
          }
        }
      });
    }
  }
});
