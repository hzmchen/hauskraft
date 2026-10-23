// SPDX-License-Identifier: MIT
// M1S-E05 Settings → Account and M1S-E07 sign-in cases, on the demo stack with throwaway members created by the
// demo owner (demo's and alex's passwords never change).
import type { Page } from "@playwright/test";
import { Api, MEMBER_PASSWORD, memberName, TEMP_PASSWORD } from "./support/api";
import { expect, story, test } from "./support/stories";
import {
  chooseNewPassword, DEACTIVATED, passwordField, SESSION_ENDED, signIn, ui,
} from "./support/ui";

type Member = { id: string; username: string; password: string };
// Red stories fail fast instead of waiting for the 120 s test timeout on a missing element.
test.use({ actionTimeout: 15_000 });
let owner: Api;
const created: string[] = [];

test.beforeAll(async () => {
  owner = await Api.login("demo").catch(() => undefined as unknown as Api);
});

test.afterAll(async () => {
  for (const id of created) await owner?.deactivate(id).catch(() => undefined);
  await owner?.dispose();
});

/** A member created by the demo owner; `ready` also replaces the temporary password through the API. */
async function member(ready = true): Promise<Member> {
  const username = memberName();
  const m = await owner.createMember({ username, "display_name": `E2E ${username}` });
  created.push(m.id);
  if (!ready) return { id: m.id, username, password: TEMP_PASSWORD };
  const api = await Api.login(username, TEMP_PASSWORD);
  try {
    await api.changePassword(TEMP_PASSWORD, MEMBER_PASSWORD);
    await api.logout(); // the helper's own session must not count as one of the member's devices
  } finally {
    await api.dispose();
  }
  return { id: m.id, username, password: MEMBER_PASSWORD };
}

async function signedIn(page: Page, m: Member): Promise<void> {
  await signIn(page, m.username, m.password);
  await expect(page).toHaveURL(/\/today$/);
}

// ---------------------------------------------------------------- M1S-E05-03 profile and password
test("profile: display name and language", story("M1S-E05-03"), async ({ page }) => {
  const m = await member();
  await signedIn(page, m);
  await page.goto("/settings/account");
  const profile = page.getByRole("region", { name: "Profile" });
  await expect(profile).toContainText(m.username);
  await profile.getByRole("textbox", { name: "Display name" }).fill("Renamed in E2E");
  await profile.getByRole("button", { name: "Save profile" }).click();
  await expect(page.getByText("Profile saved")).toBeVisible();
  await page.reload();
  await expect(page.getByRole("region", { name: "Profile" }).getByRole("textbox", { name: "Display name" }))
    .toHaveValue("Renamed in E2E");
});

test("password: mismatch, wrong current password, success", story("M1S-E05-03", "M1S-E07-04"), async ({ page }) => {
  const m = await member();
  await signedIn(page, m);
  await page.goto("/settings/account");
  const pw = page.getByRole("region", { name: "Password" });
  await expect(pw.getByText("At least 12 characters")).toBeVisible();
  await expect(passwordField(pw, "Current password")).toHaveAttribute("autocomplete", "current-password");
  await expect(passwordField(pw, "New password")).toHaveAttribute("autocomplete", "new-password");
  await expect(passwordField(pw, "Repeat new password")).toHaveAttribute("autocomplete", "new-password");

  await passwordField(pw, "Current password").fill(m.password);
  await passwordField(pw, "New password").fill("brand-new-password-1");
  await passwordField(pw, "Repeat new password").fill("brand-new-password-2");
  await pw.getByRole("button", { name: "Change password" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Passwords do not match" })).toBeVisible();

  await passwordField(pw, "Current password").fill("not-the-current-one");
  await passwordField(pw, "Repeat new password").fill("brand-new-password-1");
  await pw.getByRole("button", { name: "Change password" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "The current password is wrong." })).toBeVisible();
  await expect(page.getByText("Password changed")).toHaveCount(0);

  await passwordField(pw, "Current password").fill(m.password);
  await pw.getByRole("button", { name: "Change password" }).click();
  await expect(page.getByText("Password changed")).toBeVisible();
  const check = await Api.login(m.username, "brand-new-password-1");
  await check.dispose();
});

// ---------------------------------------------------------------- M1S-E05-04 devices
test("devices: sign out another device, then everywhere", story("M1S-E05-04"), async ({ page, browser }) => {
  const m = await member();
  const otherCtx = await browser.newContext();
  const other = await otherCtx.newPage();
  try {
    await signedIn(other, m);
    await signedIn(page, m);
    await page.goto("/settings/account");
    const devices = page.getByRole("list", { name: "Signed-in devices" });
    await expect(devices.getByRole("listitem")).toHaveCount(2);
    const current = devices.getByRole("listitem").filter({ hasText: "This device" });
    await expect(current).toHaveCount(1);
    await expect(current.getByRole("button", { name: "Sign out" })).toHaveCount(0);
    await devices.getByRole("listitem").filter({ hasNotText: "This device" }).getByRole("button", { name: "Sign out" })
      .click();
    await expect(devices.getByRole("listitem")).toHaveCount(1);
    await other.reload();
    await expect(other).toHaveURL(/\/login/);

    await page.getByRole("button", { name: "Sign out everywhere" }).click();
    const confirm = page.getByRole("alertdialog", { name: "Sign out everywhere?" });
    await confirm.getByRole("button", { name: "Sign out everywhere" }).click();
    await expect(page).toHaveURL(/\/login/);
    await page.goto("/today");
    await expect(page).toHaveURL(/\/login/);
  } finally {
    await otherCtx.close();
  }
});

// ---------------------------------------------------------------- M1S-E07-02 forced password change
test("a temporary password leads to the change page, then to the original target", story("M1S-E07-02", "M1S-E07-04"),
  async ({ page }) => {
    const m = await member(false);
    await page.goto("/p/tasks");
    await expect(page).toHaveURL(/\/login\?.*redirect=/);
    await signIn(page, m.username, m.password);
    await expect(page.getByText("Your password was set by someone else. Choose your own to continue.")).toBeVisible();
    await expect(page.getByText("At least 12 characters")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Main" })).toHaveCount(0);
    await page.goto("/activity"); // any app route leads back here, remembering where I wanted to go
    await expect(page).toHaveURL(/\/change-password/);
    await chooseNewPassword(page, m.password, MEMBER_PASSWORD);
    await expect(page).toHaveURL(/\/activity$/);
    await expect(ui.nav(page)).toBeVisible();
  });

// ---------------------------------------------------------------- M1S-E07-03 session ended
test("an ended session explains itself and returns to the page", story("M1S-E07-03"), async ({ page }) => {
  const m = await member();
  await signedIn(page, m);
  const api = await Api.login(m.username, m.password);
  await api.logoutEverywhere();
  await api.dispose();
  await ui.addTask(page).fill("After my session ended");
  await ui.addTask(page).press("Enter");
  await expect(page).toHaveURL(/\/login\?.*reason=expired/);
  await expect(page.getByText(SESSION_ENDED)).toBeVisible();
  await signIn(page, m.username, m.password);
  await expect(page).toHaveURL(/\/today$/);
});

test("signing out on purpose shows no session message", story("M1S-E07-03"), async ({ page }) => {
  const m = await member();
  await signedIn(page, m);
  await page.getByRole("button", { name: "Account menu" }).click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByText(SESSION_ENDED)).toHaveCount(0);
});

test("only same-origin paths are followed after sign-in", story("M1S-E07-03"), async ({ page }) => {
  const m = await member();
  for (const target of ["//evil.example/x", "https://evil.example/", "javascript:alert(1)"]) {
    await page.goto(`/login?redirect=${encodeURIComponent(target)}`);
    await signIn(page, m.username, m.password);
    await expect(page).toHaveURL(/^http:\/\/[^/]+\/today$/);
    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("menuitem", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login/);
  }
});

// ---------------------------------------------------------------- M1S-E07-04 deactivated, autocomplete
test("a deactivated account gets a clear message", story("M1S-E07-04"), async ({ page }) => {
  const m = await member();
  await owner.deactivate(m.id);
  await page.goto("/login");
  await expect(page.getByRole("textbox", { name: "Username" })).toHaveAttribute("autocomplete", "username");
  await expect(passwordField(page, "Password")).toHaveAttribute("autocomplete", "current-password");
  await signIn(page, m.username, m.password);
  await expect(page.getByRole("alert").filter({ hasText: DEACTIVATED })).toBeVisible();
  await signIn(page, m.username, "wrong-password-0000");
  await expect(page.getByRole("alert").filter({ hasText: "Wrong username or password" })).toBeVisible();
});
