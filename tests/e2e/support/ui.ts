// SPDX-License-Identifier: MIT
// Page helpers built only on roles and accessible names from docs/testing/ui-contract.md.
// If the UI changes an accessible name, update the contract first (with the spec owner), then this file.
import { expect, type Locator, type Page } from "@playwright/test";
import { PASSWORD } from "./api";

export const ui = {
  nav: (page: Page) => page.getByRole("navigation", { name: "Main" }),
  main: (page: Page) => page.getByRole("main"),
  tasksWidget: (page: Page, name = "Tasks") => page.getByRole("region", { name }),
  openList: (page: Page) => page.getByRole("list", { name: "Open tasks" }),
  doneList: (page: Page) => page.getByRole("list", { name: "Done tasks" }),
  addTask: (page: Page, name = "Add a task") => page.getByRole("textbox", { name }),
  // `has` resolves its locator inside each list item, so it must start from the page, not from `scope`.
  row: (scope: Page | Locator, title: string) =>
    scope.getByRole("listitem").filter({
      has: ("page" in scope ? scope.page() : scope).getByRole("checkbox", { name: `Mark '${title}' as done` }),
    }),
  checkbox: (scope: Page | Locator, title: string) => scope.getByRole("checkbox", { name: `Mark '${title}' as done` }),
};

export async function login(page: Page, username = "demo", password = PASSWORD): Promise<void> {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "Username" }).fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/today$/);
}

/** Navigation item names in order; opens a drawer first if the active nav style uses one. */
export async function navItems(page: Page): Promise<string[]> {
  const opener = page.getByRole("button", { name: "Open menu" });
  if (await opener.isVisible()) await opener.click();
  const names = await ui.nav(page).getByRole("link").allInnerTexts();
  if (await opener.isVisible().catch(() => false)) await page.keyboard.press("Escape");
  return names.map((n) => n.trim());
}

export async function goNav(page: Page, name: string): Promise<void> {
  const opener = page.getByRole("button", { name: "Open menu" });
  if (await opener.isVisible()) await opener.click();
  await ui.nav(page).getByRole("link", { name }).click();
}

export async function htmlAttr(page: Page, name: string): Promise<string | null> {
  return page.locator("html").getAttribute(name);
}

export async function isDark(page: Page): Promise<boolean> {
  return page.evaluate(() => document.documentElement.classList.contains("dark"));
}

/** Marks the current document so a later check can prove no full reload happened. */
export async function markDocument(page: Page): Promise<void> {
  await page.evaluate(() => ((window as unknown as { __hauskraftMark?: number }).__hauskraftMark = 42));
}

export async function documentStillMarked(page: Page): Promise<boolean> {
  return page.evaluate(() => (window as unknown as { __hauskraftMark?: number }).__hauskraftMark === 42);
}

/** Choose an option whether "Sort by" is a native <select> or an ARIA combobox. */
export async function chooseOption(page: Page, comboName: string, option: string): Promise<void> {
  const combo = page.getByRole("combobox", { name: comboName });
  try {
    await combo.selectOption({ label: option }, { timeout: 2_000 });
  } catch {
    await combo.click();
    await page.getByRole("option", { name: option }).click();
  }
}
