// SPDX-License-Identifier: MIT
// M1S-E08 settings shell on the demo stack (demo = owner, alex = adult): sections per role, Appearance for adults,
// the account menu entry, and function invariance of every new settings view across themes (spec §10.2.2).
import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import { Api, THEMES } from "./support/api";
import { expect, story, test } from "./support/stories";
import { goNav, htmlAttr, login, navItems, settingsNav, settingsSections, ui } from "./support/ui";

const THEME_IDS = [THEMES.default, THEMES.paper, THEMES.hackspace];
const MODES = ["light", "dark"] as const;
const VIEWPORTS = { wide: { width: 1280, height: 800 }, narrow: { width: 390, height: 844 } };

// Red stories fail fast instead of waiting for the 120 s test timeout on a missing element.
test.use({ actionTimeout: 15_000 });

test.describe("sections follow the role", () => {
  test("owners see four sections; /settings still opens Appearance", story("M1S-E08-01"), async ({ page }) => {
    await login(page, "demo");
    await goNav(page, "Settings");
    await expect(page).toHaveURL(/\/settings\/appearance$/);
    expect(await settingsSections(page)).toEqual(["Appearance", "Account", "Household", "Members"]);
    for (const section of ["Account", "Household", "Members", "Appearance"]) {
      await settingsNav(page).getByRole("link", { name: section, exact: true }).click();
      await expect(page.getByRole("heading", { level: 1, name: section })).toBeVisible();
    }
    expect(await navItems(page)).toEqual(["Today", "Tasks", "Activity", "Settings"]);
  });

  test("adults see Appearance and Account only", story("M1S-E08-01"), async ({ page }) => {
    await login(page, "alex");
    await goNav(page, "Settings");
    expect(await settingsSections(page)).toEqual(["Appearance", "Account"]);
    for (const route of ["/settings/household", "/settings/members"]) {
      await page.goto(route);
      await expect(page).toHaveURL(/\/settings\/appearance$/);
    }
    expect(await navItems(page)).toEqual(["Today", "Tasks", "Activity", "Settings"]);
  });

  test("section names are translated", story("M1S-E08-01"), async ({ page }) => {
    const api = await Api.login("demo");
    try {
      await api.setLocale("de");
      await login(page, "demo");
      await page.goto("/settings/appearance");
      expect(await settingsSections(page)).toEqual(["Darstellung", "Konto", "Haushalt", "Mitglieder"]);
    } finally {
      await api.setLocale("en");
      await api.dispose();
    }
  });
});

test.describe("Appearance for adults", () => {
  test("the household theme is read-only, the colour mode is not", story("M1S-E08-02"), async ({ page }) => {
    await login(page, "alex");
    await page.goto("/settings/appearance");
    const theme = page.getByRole("region", { name: "Household theme" });
    await expect(theme).toContainText("Only owners can change the household theme.");
    const group = page.getByRole("radiogroup", { name: "Household theme" });
    await expect(group.getByRole("radio").first()).toBeVisible();
    await expect(group.getByRole("radio", { disabled: false })).toHaveCount(0);
    await expect(group.getByRole("radio", { checked: true })).toHaveCount(1);
    const mode = page.getByRole("radiogroup", { name: "Colour mode" });
    await mode.getByRole("radio", { name: "Dark" }).check();
    expect(await page.evaluate(() => document.documentElement.classList.contains("dark"))).toBe(true);
    await mode.getByRole("radio", { name: "System" }).check();
  });

  // Regression guard: owners keep the M0* behaviour, so this test is tagged with the M0* story it protects.
  test("owners can still change the theme", story("M0S-E13-07"), async ({ page }) => {
    await login(page, "demo");
    await page.goto("/settings/appearance");
    await expect(page.getByRole("radiogroup", { name: "Household theme" })).toBeVisible();
    await expect(page.getByText("Only owners can change the household theme.")).toHaveCount(0);
    const group = page.getByRole("radiogroup", { name: "Household theme" });
    await expect(group.getByRole("radio", { name: "Paper", disabled: false })).toBeVisible();
  });
});

test("the account menu opens account settings", story("M1S-E08-03"), async ({ page }) => {
  await login(page, "demo");
  await page.getByRole("button", { name: "Account menu" }).click();
  const items = page.getByRole("menuitem");
  await expect(page.getByRole("menuitem", { name: "Account settings" })).toBeVisible();
  const names = (await items.allInnerTexts()).map((n) => n.trim());
  expect(names.indexOf("Account settings")).toBeLessThan(names.indexOf("Sign out"));
  await page.getByRole("menuitem", { name: "Account settings" }).click();
  await expect(page).toHaveURL(/\/settings\/account$/);
  await expect(page.getByRole("heading", { level: 1, name: "Account" })).toBeVisible();
});

// ---------------------------------------------------------------- invariance (spec §10.2.2)
type View = { path: string; user: "demo" | "alex"; stories: string[] };
const VIEWS: View[] = [
  { path: "/settings/appearance", user: "alex", stories: ["M1S-E08-02"] },
  { path: "/settings/account", user: "demo", stories: ["M1S-E05-03", "M1S-E05-04"] },
  { path: "/settings/account", user: "alex", stories: ["M1S-E05-03", "M1S-E05-04"] },
  { path: "/settings/household", user: "demo", stories: ["M1S-E04-02"] },
  { path: "/settings/members", user: "demo", stories: ["M1S-E06-05"] },
];

const GROWING_LISTS = /^(\s*)- list "(Signed-in devices|Members)"/;

/** Mask what legitimately differs between captures: the selected theme and lists that grow with each sign-in. */
function normalise(snapshot: string): string {
  const out: string[] = [];
  let maskDepth = -1;
  for (const line of snapshot.replace(/(radio "[^"]+") \[checked\]/g, "$1").split("\n")) {
    const depth = line.length - line.trimStart().length;
    if (maskDepth >= 0 && depth > maskDepth) continue;
    maskDepth = -1;
    out.push(line);
    const m = GROWING_LISTS.exec(line);
    if (m) {
      maskDepth = m[1].length;
      out.push(`${m[1]}  - <masked>`);
    }
  }
  return out.join("\n");
}

async function capture(page: Page, view: string) {
  await page.goto(view);
  await ui.main(page).waitFor();
  await expect(settingsNav(page)).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  return { main: normalise(await ui.main(page).ariaSnapshot()), nav: await navItems(page) };
}

test.describe("settings views are function-invariant across themes", () => {
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
      test(`${view.path} as ${view.user} @ ${vpName}`, story("M1S-E08-01", ...view.stories), async ({ browser }) => {
        let baseline: Awaited<ReturnType<typeof capture>> | undefined;
        for (const themeId of THEME_IDS) {
          await api.setTheme(themeId);
          for (const mode of MODES) {
            const ctx = await browser.newContext({ viewport, colorScheme: mode });
            await ctx.addInitScript((m) => {
              try { localStorage.setItem("hauskraft.mode", m); } catch { /* storage blocked */ }
            }, mode);
            const page = await ctx.newPage();
            await login(page, view.user);
            await page.goto(view.path);
            await expect.poll(() => htmlAttr(page, "data-hauskraft-theme")).toBe(themeId);
            const got = await capture(page, view.path);
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
