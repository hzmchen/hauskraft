// SPDX-License-Identifier: MIT
// M1S-E04 household settings on the demo stack: the Household page, the browser title and "today" in the
// household time zone. The household settings are restored afterwards.
import { Api } from "./support/api";
import { expect, story, test } from "./support/stories";
import { chooseOption, login, openSettings, ui } from "./support/ui";

test.describe.configure({ mode: "serial" });
// Red stories fail fast instead of waiting for the 120 s test timeout on a missing element.
test.use({ actionTimeout: 15_000 });

const KIRITIMATI = "Pacific/Kiritimati"; // UTC+14
const VIENNA = "Europe/Vienna";
let api: Api;
let before: { name: string; timezone: string; locale: "en" | "de" } | undefined;
const tasks: string[] = [];

test.beforeAll(async () => {
  api = await Api.login("demo").catch(() => undefined as unknown as Api);
  before = await api?.household().catch(() => undefined);
});

test.afterAll(async () => {
  for (const id of tasks) await api?.deleteTask(id).catch(() => undefined);
  if (before) await api?.setHousehold(before).catch(() => undefined);
  await api?.dispose();
});

test("owners edit the household on its page", story("M1S-E04-02"), async ({ page }) => {
  await login(page, "demo");
  await openSettings(page, "Household");
  const name = page.getByRole("textbox", { name: "Household name" });
  await expect(name).toHaveValue(before?.name ?? "Demo household");
  await name.fill("E2E household");
  await chooseOption(page, "Time zone", VIENNA);
  await chooseOption(page, "Default language", "Deutsch");
  await page.getByRole("button", { name: "Save household" }).click();
  await expect(page.getByText("Household saved")).toBeVisible();
  expect(await api.household()).toEqual({ "name": "E2E household", timezone: VIENNA, locale: "de" });
  await page.reload();
  await expect(page.getByRole("textbox", { name: "Household name" })).toHaveValue("E2E household");
  if (before) await api.setHousehold(before);
});

test("the browser title carries the page and the household", story("M1S-E04-04"), async ({ page }) => {
  await login(page, "demo");
  await expect(page).toHaveTitle(`Today · ${before?.name ?? "Demo household"}`);
  await api.setHousehold({ "name": "Title Test Household" });
  await expect(page).toHaveTitle("Today · Title Test Household", { timeout: 70_000 });
  await page.goto("/settings/household");
  await expect(page).toHaveTitle("Household · Title Test Household");
  await page.goto("/p/tasks");
  await expect(page).toHaveTitle("All tasks · Title Test Household");
  if (before) await api.setHousehold(before);
  await page.getByRole("button", { name: "Account menu" }).click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(page).toHaveTitle("Hauskraft");
});

test("due badges count today in the household time zone", story("M1S-E04-03"), async ({ browser }) => {
  // 2026-11-02 23:30 in Berlin (the browser) is already 2026-11-03 12:30 in Kiritimati (the household).
  await api.setHousehold({ timezone: KIRITIMATI });
  for (const [title, due] of [["Kiritimati today", "2026-11-03"], ["Kiritimati yesterday", "2026-11-02"]]) {
    tasks.push((await api.createTask(title, due)).id);
  }
  const ctx = await browser.newContext({ timezoneId: "Europe/Berlin" });
  await ctx.clock.setFixedTime(new Date("2026-11-02T23:30:00+01:00"));
  const page = await ctx.newPage();
  try {
    await login(page, "demo");
    const widget = ui.tasksWidget(page);
    await expect(ui.row(widget, "Kiritimati today")).toContainText("Today");
    await expect(ui.row(widget, "Kiritimati yesterday")).toContainText("Overdue");
    await page.goto("/p/tasks");
    await expect(ui.row(page, "Kiritimati today")).toContainText("Today");
    await expect(ui.row(page, "Kiritimati yesterday")).toContainText("Overdue");
  } finally {
    await ctx.close();
    if (before) await api.setHousehold({ timezone: before.timezone });
  }
});
