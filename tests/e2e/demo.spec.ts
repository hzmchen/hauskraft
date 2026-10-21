// SPDX-License-Identifier: MIT
// The M0* demo script (docs/backlog/m0-star/README.md, "Milestone acceptance criteria"), steps 1-11.
// Step 12 (CI green) is checked by CI itself. Steps share one browser session and run in order.
import { execSync } from "node:child_process";
import type { BrowserContext, Page } from "@playwright/test";
import { Api, BASE_URL, isoDate, THEMES } from "./support/api";
import { expect, story, test } from "./support/stories";
import {
  chooseOption, documentStillMarked, goNav, htmlAttr, isDark, login, markDocument, navItems, ui,
} from "./support/ui";

test.describe.configure({ mode: "serial" });

const DEMO = "M0S-E11-03";
let ctx: BrowserContext;
let page: Page;
let alexCtx: BrowserContext;
let alexPage: Page;
let navBefore: string[] = [];
const persistTitle = `Persist me ${Date.now().toString(36)}`;

test.beforeAll(async ({ browser }) => {
  ctx = await browser.newContext({ colorScheme: "light" });
  page = await ctx.newPage();
});

test.afterAll(async () => {
  try {
    const api = await Api.login("demo");
    await api.setTheme(THEMES.default);
    await api.setLocale("en");
    await api.dispose();
  } catch {
    // stack not running (red phase): nothing to clean up
  }
  await alexCtx?.close();
  await ctx?.close();
});

test("1 · stack starts and serves the login page", story(DEMO, "M0S-E11-01", "M0S-E03-02"), async ({ request }) => {
  const ready = await request.get(`${BASE_URL}/api/v1/readyz`);
  expect(ready.status()).toBe(200);
  await page.goto("/");
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});

test("2 · demo logs in and sees seeded tasks in the Default theme",
  story(DEMO, "M0S-E11-02", "M0S-E08-03", "M0S-E08-06", "M0S-E07-04", "M0S-E09-01"), async () => {
    await login(page, "demo");
    expect(await htmlAttr(page, "data-hauskraft-theme")).toBe(THEMES.default);
    const widget = ui.tasksWidget(page);
    await expect(widget).toBeVisible();
    await expect(ui.checkbox(widget, "Water the plants")).toBeVisible();
    await expect(ui.row(widget, "Take out recycling")).toContainText(/Due|Today|Overdue/);
    await expect(widget.getByRole("button", { name: /Show done \(\d+\)/ })).toBeVisible();
    navBefore = await navItems(page);
    expect(navBefore).toEqual(["Today", "Tasks", "Activity", "Settings"]);
  });

test("3 · quick add puts the task on top without a reload", story(DEMO, "M0S-E09-01"), async () => {
  await markDocument(page);
  const input = ui.addTask(page);
  await input.fill("Buy milk");
  await input.press("Enter");
  await expect(input).toHaveValue("");
  const first = ui.openList(page).getByRole("listitem").first();
  await expect(first.getByRole("checkbox", { name: "Mark 'Buy milk' as done" })).toBeVisible();
  expect(await documentStillMarked(page)).toBe(true);
});

test("4 · rename inline, set a due date, see the badge", story(DEMO, "M0S-E09-01", "M0S-E09-02"), async () => {
  const widget = ui.tasksWidget(page);
  await widget.getByRole("button", { name: "Edit 'Buy milk'" }).click();
  const title = widget.getByRole("textbox", { name: "Task title" });
  await title.fill("Buy oat milk");
  await title.press("Enter");
  await expect(ui.checkbox(widget, "Buy oat milk")).toBeVisible();

  await goNav(page, "Tasks");
  await page.getByLabel("Due date for 'Buy oat milk'").fill(isoDate(1));
  await page.getByLabel("Due date for 'Buy oat milk'").press("Tab");
  await goNav(page, "Today");
  await expect(ui.row(ui.tasksWidget(page), "Buy oat milk")).toContainText(/Due/);
});

test("5 · tick and untick", story(DEMO, "M0S-E09-01"), async () => {
  const widget = ui.tasksWidget(page);
  await ui.checkbox(widget, "Buy oat milk").check();
  await expect(ui.openList(page).getByRole("checkbox", { name: "Mark 'Buy oat milk' as done" })).toHaveCount(0);
  await widget.getByRole("button", { name: /Show done \(\d+\)/ }).click();
  const done = ui.checkbox(ui.doneList(page), "Buy oat milk");
  await expect(done).toBeChecked();
  await done.uncheck();
  await expect(ui.checkbox(ui.openList(page), "Buy oat milk")).not.toBeChecked();
});

test("6 · All tasks page filters, sorts and deletes with confirmation",
  story(DEMO, "M0S-E09-02", "M0S-E08-05"), async () => {
    await goNav(page, "Tasks");
    await expect(page).toHaveURL(/\/p\/tasks/);
    await expect(page.getByRole("heading", { level: 1, name: "All tasks" })).toBeVisible();
    for (const tab of ["Open", "Done", "All"]) {
      await expect(page.getByRole("tab", { name: tab })).toBeVisible();
    }
    await page.getByRole("tab", { name: "Done" }).click();
    await expect(page).toHaveURL(/status=done/);
    await page.getByRole("tab", { name: "All" }).click();
    await chooseOption(page, "Sort by", "Due date");
    await chooseOption(page, "Sort by", "Created");
    await page.getByRole("button", { name: "Delete 'Buy oat milk'" }).click();
    const dialog = page.getByRole("alertdialog", { name: "Delete task?" }).or(
      page.getByRole("dialog", { name: "Delete task?" }));
    await dialog.getByRole("button", { name: "Delete" }).click();
    await expect(page.getByRole("checkbox", { name: "Mark 'Buy oat milk' as done" })).toHaveCount(0);
  });

test("7 · Activity shows who did what", story(DEMO, "M0S-E10-03"), async () => {
  await goNav(page, "Activity");
  const feed = page.getByRole("list", { name: "Activity" });
  await expect(feed).toContainText("Demo Adult added 'Buy milk'");
  await expect(feed).toContainText(/Demo Adult updated '.*oat milk'/);
  await expect(feed).toContainText("Demo Adult completed 'Buy oat milk'");
  await expect(feed).toContainText("Demo Adult deleted 'Buy oat milk'");
});

test("8 · switching the household theme changes the look, not the functions",
  story(DEMO, "M0S-E13-07", "M0S-E13-05", "M0S-E13-04"), async ({ browser }) => {
    alexCtx = await browser.newContext({ colorScheme: "light" });
    alexPage = await alexCtx.newPage();
    await login(alexPage, "alex");
    await markDocument(alexPage);

    await goNav(page, "Settings");
    await expect(page).toHaveURL(/\/settings\/appearance/);
    const household = page.getByRole("region", { name: "Household theme" });
    await expect(household).toContainText("Applies to everyone on every device");
    await household.getByRole("radio", { name: "Hackspace" }).check();
    await page.getByRole("dialog", { name: "Change the look for everyone?" })
      .getByRole("button", { name: "Change theme" }).click();
    await expect.poll(() => htmlAttr(page, "data-hauskraft-theme")).toBe(THEMES.hackspace);
    expect(await ui.nav(page).getAttribute("data-nav-style")).toBe("topbar");

    await goNav(page, "Today");
    expect(await navItems(page)).toEqual(navBefore);
    await expect(ui.addTask(page)).toBeVisible();
    await expect(ui.tasksWidget(page).getByRole("link", { name: "All tasks" })).toBeVisible();

    await expect.poll(() => htmlAttr(alexPage, "data-hauskraft-theme"), { timeout: 65_000 }).toBe(THEMES.hackspace);
    expect(await documentStillMarked(alexPage)).toBe(true);
  });

test("9 · colour mode is per device", story(DEMO, "M0S-E08-02", "M0S-E13-07"), async () => {
  await goNav(page, "Settings");
  await page.getByRole("region", { name: "This device" }).getByRole("radio", { name: "Dark" }).check();
  expect(await isDark(page)).toBe(true);
  expect(await isDark(alexPage)).toBe(false);
  await page.reload();
  await alexPage.reload();
  expect(await isDark(page)).toBe(true);
  expect(await isDark(alexPage)).toBe(false);
});

test("10 · German UI, theme names unchanged", story(DEMO, "M0S-E08-04", "M0S-E09-03"), async () => {
  await page.getByRole("button", { name: "Account menu" }).click();
  await page.getByRole("menuitemradio", { name: "Deutsch" }).click();
  await expect(ui.nav(page).getByRole("link", { name: "Heute" })).toBeVisible();
  await page.reload();
  await expect(ui.nav(page).getByRole("link", { name: "Heute" })).toBeVisible();
  await goNav(page, "Einstellungen");
  await expect(page.getByRole("radio", { name: "Hackspace" })).toBeVisible();
  await goNav(page, "Heute");
  await expect(ui.tasksWidget(page, "Aufgaben")).toBeVisible();
});

test("11 · everything survives a restart", story(DEMO, "M0S-E11-01"), async () => {
  const restart = process.env.HAUSKRAFT_E2E_RESTART_CMD;
  test.skip(!restart, "set HAUSKRAFT_E2E_RESTART_CMD (CI: 'docker compose ... down && ... up --wait')");
  const input = ui.addTask(page, "Aufgabe hinzufügen");
  await input.fill(persistTitle);
  await input.press("Enter");
  execSync(restart!, { stdio: "inherit", timeout: 300_000 });
  await page.goto("/today");
  if (/\/login/.test(page.url())) await login(page, "demo");
  await expect.poll(() => htmlAttr(page, "data-hauskraft-theme")).toBe(THEMES.hackspace);
  await expect(ui.nav(page).getByRole("link", { name: "Heute" })).toBeVisible();
  await expect(page.getByRole("checkbox", { name: new RegExp(persistTitle) })).toBeVisible();
  const api = await Api.login("demo");
  const tasks = await (await api.ctx.get("tasks", { params: { limit: 200 } })).json();
  for (const t of tasks.items) if (t.title === persistTitle) await api.deleteTask(t.id);
  await api.dispose();
});
