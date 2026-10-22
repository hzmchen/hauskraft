// SPDX-License-Identifier: MIT
// M1S-E06-05 Settings → Members on the demo stack (demo = owner). Members created here are throwaway accounts and
// are deactivated afterwards; demo and alex are never changed.
import { Api, memberName, TEMP_PASSWORD } from "./support/api";
import { expect, story, test } from "./support/stories";
import { chooseNewPassword, chooseOption, goNav, login, openSettings, passwordField, signIn } from "./support/ui";

test.describe.configure({ mode: "serial" });
// Red stories fail fast instead of waiting for the 120 s test timeout on a missing element.
test.use({ actionTimeout: 15_000 });

const STORY = "M1S-E06-05";
const ALEX = "Alex Adult";
const DEMO_OWNER = "Demo Adult";
const username = memberName();
let displayName = `E2E Member ${username.slice(3, 7)}`;
let owner: Api;

test.beforeAll(async () => {
  owner = await Api.login("demo").catch(() => undefined as unknown as Api);
});

test.afterAll(async () => {
  const m = await owner?.findMember(username).catch(() => undefined);
  if (m) await owner.deactivate(m.id).catch(() => undefined);
  await owner?.dispose();
});

test("the list shows every member with role and the per-member actions", story(STORY), async ({ page }) => {
  await login(page, "demo");
  await openSettings(page, "Members");
  const list = page.getByRole("list", { name: "Members" });
  await expect(list.getByRole("listitem").filter({ hasText: "alex" })).toContainText("Adult");
  await expect(list.getByRole("listitem").filter({ hasText: "demo" })).toContainText("Owner");
  await expect(page.getByRole("button", { name: `Edit ${ALEX}` })).toBeVisible();
  await expect(page.getByRole("button", { name: `Reset password for ${ALEX}` })).toBeVisible();
  await expect(page.getByRole("button", { name: `Deactivate ${ALEX}` })).toBeVisible();
  await expect(page.getByRole("button", { name: `Reset password for ${DEMO_OWNER}` })).toHaveCount(0);
});

test("add a member", story(STORY, "M1S-E09-02"), async ({ page }) => {
  await login(page, "demo");
  await openSettings(page, "Members");
  await page.getByRole("button", { name: "Add member" }).click();
  let dialog = page.getByRole("dialog", { name: "Add member" });
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(dialog).toBeHidden();

  await page.getByRole("button", { name: "Add member" }).click();
  dialog = page.getByRole("dialog", { name: "Add member" });
  await dialog.getByRole("textbox", { name: "Display name" }).fill(displayName);
  await dialog.getByRole("textbox", { name: "Username" }).fill(username);
  await chooseOption(page, "Role", "Adult");
  await expect(passwordField(dialog, "Temporary password")).toHaveAttribute("autocomplete", "new-password");
  await passwordField(dialog, "Temporary password").fill(TEMP_PASSWORD);
  await dialog.getByRole("button", { name: "Add member" }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByRole("list", { name: "Members" }).getByRole("listitem").filter({ hasText: username }))
    .toContainText("Adult");

  await goNav(page, "Activity");
  await expect(page.getByRole("list", { name: "Activity" })).toContainText(`Demo Adult added ${displayName} to the household`);
});

test("edit a member", story(STORY, "M1S-E09-02"), async ({ page }) => {
  await login(page, "demo");
  await openSettings(page, "Members");
  await page.getByRole("button", { name: `Edit ${displayName}` }).click();
  const dialog = page.getByRole("dialog", { name: "Edit member" });
  const renamed = `${displayName} R`;
  await dialog.getByRole("textbox", { name: "Display name" }).fill(renamed);
  await dialog.getByRole("button", { name: "Save" }).click();
  await expect(dialog).toBeHidden();
  displayName = renamed;
  await expect(page.getByRole("button", { name: `Edit ${displayName}` })).toBeVisible();
  await goNav(page, "Activity");
  await expect(page.getByRole("list", { name: "Activity" })).toContainText(`Demo Adult updated the account of ${displayName}`);
});

test("reset a password", story(STORY, "M1S-E09-02"), async ({ page, browser }) => {
  await login(page, "demo");
  await openSettings(page, "Members");
  await page.getByRole("button", { name: `Reset password for ${displayName}` }).click();
  const dialog = page.getByRole("dialog", { name: "Reset password?" });
  await passwordField(dialog, "Temporary password").fill("members-spec-temp-77");
  await dialog.getByRole("button", { name: "Reset password" }).click();
  await expect(dialog).toBeHidden();

  const ctx = await browser.newContext();
  try {
    const memberPage = await ctx.newPage();
    await signIn(memberPage, username, "members-spec-temp-77");
    await chooseNewPassword(memberPage, "members-spec-temp-77", "members-spec-own-88");
    await expect(memberPage).toHaveURL(/\/today$/);
  } finally {
    await ctx.close();
  }
  await goNav(page, "Activity");
  await expect(page.getByRole("list", { name: "Activity" })).toContainText(`Demo Adult reset the password of ${displayName}`);
});

test("deactivate after confirming, then reactivate", story(STORY, "M1S-E09-02"), async ({ page }) => {
  await login(page, "demo");
  await openSettings(page, "Members");
  const row = page.getByRole("list", { name: "Members" }).getByRole("listitem").filter({ hasText: username });
  await page.getByRole("button", { name: `Deactivate ${displayName}` }).click();
  let confirm = page.getByRole("alertdialog", { name: `Deactivate ${displayName}?` });
  await expect(confirm).toContainText("They are signed out everywhere and can't sign in until reactivated.");
  await confirm.getByRole("button", { name: "Cancel" }).click();
  await expect(row).not.toContainText("Deactivated");

  await page.getByRole("button", { name: `Deactivate ${displayName}` }).click();
  confirm = page.getByRole("alertdialog", { name: `Deactivate ${displayName}?` });
  await confirm.getByRole("button", { name: "Deactivate" }).click();
  await expect(row).toContainText("Deactivated");
  await expect(page.getByRole("button", { name: `Deactivate ${displayName}` })).toHaveCount(0);

  await page.getByRole("button", { name: `Reactivate ${displayName}` }).click();
  await expect(row).not.toContainText("Deactivated");
  await goNav(page, "Activity");
  const feed = page.getByRole("list", { name: "Activity" });
  await expect(feed).toContainText(`Demo Adult deactivated ${displayName}`);
  await expect(feed).toContainText(`Demo Adult reactivated ${displayName}`);
});
