// SPDX-License-Identifier: MIT
// Shell guard and navigation (E08-03, E08-05) and the All tasks page in detail (E09-02).
import { Api, isoDate, unique } from "./support/api";
import { expect, story, test } from "./support/stories";
import { chooseOption, login, navItems, ui } from "./support/ui";

test.describe("auth guard", () => {
  test("unauthenticated visit redirects to login and back", story("M0S-E08-03"), async ({ page }) => {
    await page.goto("/today");
    await expect(page).toHaveURL(/\/login\?redirect=%2Ftoday|\/login\?redirect=\/today/);
    await page.getByRole("textbox", { name: "Username" }).fill("demo");
    await page.getByLabel("Password").fill("wrong-password-xyz");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toContainText("Wrong username or password");
    await login(page, "demo");
  });

  test("sign out clears the session", story("M0S-E08-03"), async ({ page }) => {
    await login(page, "demo");
    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("menuitem", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login/);
    await page.goto("/today");
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe("shell", () => {
  test("navigation order, skip link and unknown pages", story("M0S-E08-05"), async ({ page }) => {
    await login(page, "demo");
    expect(await navItems(page)).toEqual(["Today", "Tasks", "Activity", "Settings"]);
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
    await page.goto("/p/does-not-exist");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/not found/i);
  });

  test("edit layout mode toggles", story("M0S-E08-06"), async ({ page }) => {
    await login(page, "demo");
    await page.getByRole("button", { name: "Edit layout" }).click();
    await expect(page.getByRole("button", { name: "Done editing" })).toBeVisible();
    await page.getByRole("button", { name: "Done editing" }).click();
    await expect(page.getByRole("button", { name: "Edit layout" })).toBeVisible();
  });
});

test.describe("All tasks page", () => {
  let api: Api;
  const made: string[] = [];
  const tag = unique("page");

  test.beforeAll(async () => {
    try {
      api = await Api.login("demo");
      for (const [label, due] of [["overdue", -1], ["today", 0], ["later", 3], ["none", null]] as const) {
        made.push((await api.createTask(`${tag} ${label}`, due === null ? undefined : isoDate(due))).id);
      }
      const done = await api.createTask(`${tag} finished`);
      made.push(done.id);
      await api.patchTask(done.id, { done: true });
    } catch {
      // red phase: no stack yet; the tests below fail as expected
    }
  });

  test.afterAll(async () => {
    for (const id of made) await api?.deleteTask(id).catch(() => undefined);
    await api?.dispose();
  });

  test("due badges use words, not just colour", story("M0S-E09-02"), async ({ page }) => {
    await login(page, "demo");
    await page.goto("/p/tasks?status=open");
    await expect(ui.row(page, `${tag} overdue`)).toContainText("Overdue");
    await expect(ui.row(page, `${tag} today`)).toContainText("Today");
    await expect(ui.row(page, `${tag} later`)).toContainText("Due");
  });

  test("sort by due date puts undated tasks last", story("M0S-E09-02"), async ({ page }) => {
    await login(page, "demo");
    await page.goto("/p/tasks?status=open");
    await chooseOption(page, "Sort by", "Due date");
    const names = (await page.getByRole("checkbox").evaluateAll((els) =>
      els.map((e) => e.getAttribute("aria-label") ?? ""))).filter((n) => n.includes(tag));
    expect(names).toEqual([
      `Mark '${tag} overdue' as done`, `Mark '${tag} today' as done`, `Mark '${tag} later' as done`,
      `Mark '${tag} none' as done`,
    ]);
  });

  test("filter state lives in the URL", story("M0S-E09-02"), async ({ page }) => {
    await login(page, "demo");
    await page.goto("/p/tasks");
    await page.getByRole("tab", { name: "Done" }).click();
    await expect(page).toHaveURL(/status=done/);
    await expect(ui.checkbox(page, `${tag} finished`)).toBeChecked();
    await expect(ui.checkbox(page, `${tag} later`)).toHaveCount(0);
    await page.reload();
    await expect(page.getByRole("tab", { name: "Done", selected: true })).toBeVisible();
  });

  test("clearing a due date and cancelling a delete", story("M0S-E09-02"), async ({ page }) => {
    await login(page, "demo");
    await page.goto("/p/tasks?status=open");
    await page.getByRole("button", { name: `Clear due date for '${tag} later'` }).click();
    await expect(ui.row(page, `${tag} later`)).not.toContainText("Due");
    await page.getByRole("button", { name: `Delete '${tag} none'` }).click();
    const dialog = page.getByRole("alertdialog", { name: "Delete task?" }).or(
      page.getByRole("dialog", { name: "Delete task?" }));
    await dialog.getByRole("button", { name: "Cancel" }).click();
    await expect(ui.checkbox(page, `${tag} none`)).toBeVisible();
  });
});
