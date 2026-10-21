// SPDX-License-Identifier: MIT
// M0S-E13-08 · Themes change the look, never the functions (spec §10.2.2).
// For each view and viewport, every built-in theme in light and dark mode must expose the same
// accessibility tree in <main> and the same navigation items, and pass axe without serious issues.
import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import { Api, THEMES } from "./support/api";
import { expect, story, test } from "./support/stories";
import { htmlAttr, login, navItems, ui } from "./support/ui";

const THEME_IDS = [THEMES.default, THEMES.paper, THEMES.hackspace];
const MODES = ["light", "dark"] as const;
const VIEWPORTS = { wide: { width: 1280, height: 800 }, narrow: { width: 390, height: 844 } };
const VIEWS = ["/today", "/p/tasks", "/activity", "/settings/appearance"];

/** Mask parts that legitimately differ between captures: the selected theme and the growing feed. */
function normalise(view: string, snapshot: string): string {
  let s = snapshot;
  if (view === "/settings/appearance") s = s.replace(/(radio "[^"]+") \[checked\]/g, "$1");
  if (view === "/activity") {
    s = s.replace(/^(\s*- listitem)\b.*$/gm, "$1: <masked>").replace(/(^\s*- listitem: <masked>\n)+/gm, "$1");
  }
  return s;
}

async function capture(page: Page, view: string) {
  await page.goto(view);
  await ui.main(page).waitFor();
  return {
    main: normalise(view, await ui.main(page).ariaSnapshot()),
    nav: await navItems(page),
  };
}

test.describe("function invariance across themes", () => {
  let api: Api;
  test.beforeAll(async () => {
    api = await Api.login("demo").catch(() => undefined as unknown as Api);
  });
  test.afterAll(async () => {
    await api?.setTheme(THEMES.default).catch(() => undefined);
    await api?.dispose();
  });

  for (const [vpName, viewport] of Object.entries(VIEWPORTS)) {
    for (const view of VIEWS) {
      test(`${view} @ ${vpName}`, story("M0S-E13-08", "M0S-E13-05", "M0S-E08-02"), async ({ browser }) => {
        let baseline: Awaited<ReturnType<typeof capture>> | undefined;
        for (const themeId of THEME_IDS) {
          await api.setTheme(themeId);
          for (const mode of MODES) {
            const ctx = await browser.newContext({ viewport, colorScheme: mode });
            await ctx.addInitScript((m) => {
              try { localStorage.setItem("hearthos.mode", m); } catch { /* storage blocked */ }
            }, mode);
            const page = await ctx.newPage();
            await login(page, "demo");
            await page.goto(view);
            await expect.poll(() => htmlAttr(page, "data-hearth-theme")).toBe(themeId);
            expect(await page.evaluate(() => document.documentElement.classList.contains("dark"))).toBe(mode === "dark");

            const got = await capture(page, view);
            if (!baseline) baseline = got;
            expect(got.nav, `${themeId}/${mode}: navigation items differ`).toEqual(baseline.nav);
            expect(got.main, `${themeId}/${mode}: accessibility tree of <main> differs`).toBe(baseline.main);

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

test.describe("visual baselines", () => {
  // /p/tasks shows the seeded due date. Pin it and the browser clock so the baselines don't change every day.
  const FIXED_NOW = new Date("2026-10-13T10:00:00+02:00");
  const FIXED_DUE = "2026-10-14";
  let api: Api;
  let dated: { id: string; due_on: string | null } | undefined;
  test.beforeAll(async () => {
    api = await Api.login("demo").catch(() => undefined as unknown as Api);
    dated = await api?.findTask("Take out recycling").catch(() => undefined);
    if (dated) await api.patchTask(dated.id, { due_on: FIXED_DUE });
  });
  test.afterAll(async () => {
    if (dated) await api?.patchTask(dated.id, { due_on: dated.due_on }).catch(() => undefined);
    await api?.setTheme(THEMES.default).catch(() => undefined);
    await api?.dispose();
  });

  for (const themeId of THEME_IDS) {
    for (const mode of MODES) {
      for (const view of ["/today", "/p/tasks"]) {
        test(`${themeId} ${mode} ${view}`, story("M0S-E13-08", "M0S-E13-06"), async ({ browser }) => {
          await api.setTheme(themeId);
          const ctx = await browser.newContext({ viewport: VIEWPORTS.wide, colorScheme: mode });
          await ctx.clock.setFixedTime(FIXED_NOW);
          const page = await ctx.newPage();
          await login(page, "demo");
          await page.goto(view);
          await expect.poll(() => htmlAttr(page, "data-hearth-theme")).toBe(themeId);
          await expect(page).toHaveScreenshot(`${themeId}-${mode}${view.replaceAll("/", "_")}.png`, {
            fullPage: true,
            mask: [page.getByRole("list", { name: "Open tasks" })],
          });
          await ctx.close();
        });
      }
    }
  }
});
