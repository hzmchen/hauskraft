// SPDX-License-Identifier: MIT
// The M1* demo script (docs/backlog/m1-star/README.md, "Milestone acceptance criteria"), steps 1-11, on the
// unseeded fresh stack (M1S-E01-01). Step 12 is settings.spec.ts plus CI. Steps share browsers and run in order.
import AxeBuilder from "@axe-core/playwright";
import type { Browser, BrowserContext, Page } from "@playwright/test";
import { Api, isoDateIn, MEMBER_PASSWORD, TEMP_PASSWORD } from "./support/api";
import { FRESH_ENABLED, FRESH_URL, resetFreshStack } from "./support/fresh";
import { expect, story, test } from "./support/stories";
import {
  chooseNewPassword, chooseOption, DEACTIVATED, goNav, isDark, LAST_OWNER, navItems, openSettings, passwordField,
  SESSION_ENDED, settingsSections, signIn, ui,
} from "./support/ui";

test.describe.configure({ mode: "serial" });
// Red stories fail fast instead of waiting for the 120 s test timeout on a missing element.
test.use({ actionTimeout: 15_000 });
test.skip(!FRESH_ENABLED, "needs the fresh stack: `just fresh-up` and HAUSKRAFT_FRESH_BASE_URL (M1S-E01-01)");

const DEMO = "M1S-E10-02";
// Keys are quoted where they hold data, so the ui-contract meta test doesn't read them as accessible names.
const MIA = { user: "mia", displayName: "Mia", password: "mia-household-pass-2026" };
const ALEX_PASSWORDS = { first: "alex-own-pass-0001", second: "alex-own-pass-0002", third: "alex-own-pass-0003" };
const RESET_TEMP = "reset-temporary-pass-42";
const ALEX_M = "Alex M.";
const BERLIN = "Europe/Berlin";
const KIRITIMATI = "Pacific/Kiritimati";

let mia: Page;
let miaCtx: BrowserContext;
let alex: Page;
let alexCtx: BrowserContext;

async function newPage(browser: Browser): Promise<[BrowserContext, Page]> {
  const ctx = await browser.newContext({ baseURL: FRESH_URL, colorScheme: "light" });
  return [ctx, await ctx.newPage()];
}

async function axeClean(page: Page): Promise<void> {
  const axe = await new AxeBuilder({ page }).analyze();
  const serious = axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(serious.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
}

test.beforeAll(async ({ browser }) => {
  if (!FRESH_ENABLED) return;
  await resetFreshStack();
  [miaCtx, mia] = await newPage(browser);
  [alexCtx, alex] = await newPage(browser);
});

test.afterAll(async () => {
  await alexCtx?.close();
  await miaCtx?.close();
});

test("1 · a fresh install shows the setup wizard", story(DEMO, "M1S-E01-01", "M1S-E03-02"), async () => {
  await mia.goto("/");
  await expect(mia).toHaveURL(/\/setup$/);
  await expect(mia.getByRole("heading", { level: 1, name: "Set up your household" })).toBeVisible();
  await expect(mia.getByText("At least 12 characters")).toBeVisible();
  await axeClean(mia);
  await mia.goto("/login");
  await expect(mia).toHaveURL(/\/setup$/, { timeout: 10_000 });
});

test("2 · Mia sets up the household in Deutsch", story(DEMO, "M1S-E03-01", "M1S-E03-02", "M1S-E04-04"), async ({
  request,
}) => {
  await mia.getByRole("textbox", { name: "Household name" }).fill("Familie Müller");
  await chooseOption(mia, "Language", "Deutsch");
  await chooseOption(mia, "Time zone", BERLIN);
  await mia.getByRole("textbox", { name: "Your name" }).fill(MIA.displayName);
  await mia.getByRole("textbox", { name: "Username" }).fill(MIA.user);
  await passwordField(mia, "Password").fill(MIA.password);
  await passwordField(mia, "Repeat password").fill("something-else-entirely");
  await mia.getByRole("button", { name: "Create household" }).click();
  await expect(mia.getByRole("alert").filter({ hasText: "Passwords do not match" })).toBeVisible();
  await passwordField(mia, "Repeat password").fill(MIA.password);
  await mia.getByRole("button", { name: "Create household" }).click();

  await expect(mia).toHaveURL(/\/today$/);
  await expect(mia.getByRole("heading", { level: 1, name: "Heute" })).toBeVisible();
  await expect(mia).toHaveTitle("Heute · Familie Müller");
  expect(await navItems(mia)).toEqual(["Heute", "Aufgaben", "Aktivität", "Einstellungen"]);

  await mia.goto("/setup");
  await expect(mia).not.toHaveURL(/\/setup/);
  const again = await request.post(`${FRESH_URL}/api/v1/setup`, {
    headers: { Origin: FRESH_URL },
    data: {
      household: { "name": "Intruder", timezone: "UTC", locale: "en" },
      owner: { "username": "intruder", "display_name": "Intruder", password: "intruder-pass-0000" },
    },
  });
  expect(again.status()).toBe(409);
  expect((await again.json()).code).toBe("setup_done");

  await mia.goto("/today");
  await mia.getByRole("button", { name: "Kontomenü" }).click();
  await mia.getByRole("menuitemradio", { name: "English" }).click();
  await expect(mia.getByRole("heading", { level: 1, name: "Today" })).toBeVisible();
});

test("3 · Mia adds Alex as an adult", story(DEMO, "M1S-E08-01", "M1S-E06-05", "M1S-E09-02"), async () => {
  await goNav(mia, "Settings");
  await expect(mia).toHaveURL(/\/settings\/appearance$/);
  // M2* adds "Assistant" after Members for owners (M2S-E07-01).
  expect((await settingsSections(mia)).filter((s) => s !== "Assistant")).toEqual([
    "Appearance", "Account", "Household", "Members",
  ]);
  await openSettings(mia, "Members");
  await mia.getByRole("button", { name: "Add member" }).click();
  const dialog = mia.getByRole("dialog", { name: "Add member" });
  await dialog.getByRole("textbox", { name: "Display name" }).fill("Alex");
  await dialog.getByRole("textbox", { name: "Username" }).fill("alex");
  await expect(dialog.getByText("At least 12 characters")).toBeVisible();
  await passwordField(dialog, "Temporary password").fill(TEMP_PASSWORD);
  await dialog.getByRole("button", { name: "Add member" }).click();
  await expect(dialog).toBeHidden();
  const members = mia.getByRole("list", { name: "Members" });
  await expect(members.getByRole("listitem").filter({ hasText: "alex" })).toContainText("Adult");

  await goNav(mia, "Activity");
  await expect(mia.getByRole("list", { name: "Activity" })).toContainText("Mia added Alex to the household");
});

test("4 · Alex must choose a password, then lands on Today", story(DEMO, "M1S-E07-01", "M1S-E07-02"), async () => {
  await signIn(alex, "alex", TEMP_PASSWORD);
  await chooseNewPassword(alex, TEMP_PASSWORD, ALEX_PASSWORDS.first, true);
  await expect(alex).toHaveURL(/\/today$/);
  await expect(alex.getByRole("heading", { level: 1, name: "Heute" })).toBeVisible();
  await alex.getByRole("button", { name: "Kontomenü" }).click();
  await alex.getByRole("menuitemradio", { name: "English" }).click();
  await ui.addTask(alex).fill("Plan the garden");
  await ui.addTask(alex).press("Enter");
  await expect(ui.checkbox(ui.tasksWidget(alex), "Plan the garden")).toBeVisible();
});

test("5 · Alex sees only what an adult may use", story(DEMO, "M1S-E08-01", "M1S-E08-02", "M1S-E02-01"), async () => {
  await goNav(alex, "Settings");
  expect(await settingsSections(alex)).toEqual(["Appearance", "Account"]);
  await expect(alex.getByText("Only owners can change the household theme.")).toBeVisible();
  const radios = alex.getByRole("radiogroup", { name: "Household theme" }).getByRole("radio");
  for (const radio of await radios.all()) await expect(radio).toBeDisabled();
  await alex.getByRole("radiogroup", { name: "Colour mode" }).getByRole("radio", { name: "Dark" }).check();
  expect(await isDark(alex)).toBe(true);
  await alex.getByRole("radiogroup", { name: "Colour mode" }).getByRole("radio", { name: "Light" }).check();
  await alex.goto("/settings/members");
  await expect(alex).toHaveURL(/\/settings\/appearance$/);
  const denied = await alexCtx.request.get(`${FRESH_URL}/api/v1/users`);
  expect(denied.status()).toBe(403);
  expect((await denied.json()).code).toBe("policy_denied");
});

test("6 · Alex manages name, password and devices", story(DEMO, "M1S-E05-03", "M1S-E05-04"), async ({ browser }) => {
  await openSettings(alex, "Account");
  const profile = alex.getByRole("region", { name: "Profile" });
  await profile.getByRole("textbox", { name: "Display name" }).fill(ALEX_M);
  await profile.getByRole("button", { name: "Save profile" }).click();
  await expect(alex.getByText("Profile saved")).toBeVisible();

  const pw = alex.getByRole("region", { name: "Password" });
  await passwordField(pw, "Current password").fill(ALEX_PASSWORDS.first);
  await passwordField(pw, "New password").fill(ALEX_PASSWORDS.second);
  await passwordField(pw, "Repeat new password").fill(ALEX_PASSWORDS.second);
  await pw.getByRole("button", { name: "Change password" }).click();
  await expect(alex.getByText("Password changed")).toBeVisible();
  await alex.reload();
  await expect(alex.getByRole("region", { name: "Profile" }).getByRole("textbox", { name: "Display name" }))
    .toHaveValue(ALEX_M);

  const [otherCtx, other] = await newPage(browser);
  try {
    await signIn(other, "alex", ALEX_PASSWORDS.second);
    await expect(other).toHaveURL(/\/today$/);
    await alex.reload();
    const devices = alex.getByRole("list", { name: "Signed-in devices" });
    await expect(devices.getByRole("listitem")).toHaveCount(2);
    await expect(devices.getByRole("listitem").filter({ hasText: "This device" })).toHaveCount(1);
    await devices.getByRole("listitem").filter({ hasNotText: "This device" }).getByRole("button", { name: "Sign out" })
      .click();
    await expect(devices.getByRole("listitem")).toHaveCount(1);
    await other.reload();
    await expect(other).toHaveURL(/\/login/);
  } finally {
    await otherCtx.close();
  }
});

test("7 · Mia resets Alex's password", story(DEMO, "M1S-E06-04", "M1S-E06-05", "M1S-E07-03"), async () => {
  await openSettings(mia, "Members");
  await mia.getByRole("button", { name: `Reset password for ${ALEX_M}` }).click();
  const dialog = mia.getByRole("dialog", { name: "Reset password?" });
  await passwordField(dialog, "Temporary password").fill(RESET_TEMP);
  await dialog.getByRole("button", { name: "Reset password" }).click();
  await expect(dialog).toBeHidden();

  await goNav(alex, "Today"); // the page's requests now answer 401
  await expect(alex).toHaveURL(/\/login\?.*reason=expired/);
  await expect(alex.getByText(SESSION_ENDED)).toBeVisible();
  await signIn(alex, "alex", RESET_TEMP);
  await chooseNewPassword(alex, RESET_TEMP, ALEX_PASSWORDS.third);
  await expect(alex).toHaveURL(/\/today$/);
});

test("8 · Mia deactivates and reactivates Alex", story(DEMO, "M1S-E06-03", "M1S-E06-05", "M1S-E07-04"), async () => {
  await mia.getByRole("button", { name: `Deactivate ${ALEX_M}` }).click();
  const confirm = mia.getByRole("alertdialog", { name: `Deactivate ${ALEX_M}?` });
  await confirm.getByRole("button", { name: "Deactivate" }).click();
  const row = mia.getByRole("list", { name: "Members" }).getByRole("listitem").filter({ hasText: "alex" });
  await expect(row).toContainText("Deactivated");

  await alex.reload();
  await expect(alex).toHaveURL(/\/login/);
  await signIn(alex, "alex", ALEX_PASSWORDS.third);
  await expect(alex.getByRole("alert").filter({ hasText: DEACTIVATED })).toBeVisible();
  await expect(alex.getByRole("textbox", { name: "Username" })).toHaveAttribute("autocomplete", "username");
  await expect(passwordField(alex, "Password")).toHaveAttribute("autocomplete", "current-password");

  await goNav(mia, "Activity");
  await expect(mia.getByRole("list", { name: "Activity" })).toContainText("Alex M. added 'Plan the garden'");
  await expect(mia.getByRole("list", { name: "Activity" })).toContainText("Mia deactivated Alex M.");

  await openSettings(mia, "Members");
  await mia.getByRole("button", { name: `Reactivate ${ALEX_M}` }).click();
  await expect(row).not.toContainText("Deactivated");
  await signIn(alex, "alex", ALEX_PASSWORDS.third);
  await expect(alex).toHaveURL(/\/today$/);
});

test("9 · the last owner stays an owner", story(DEMO, "M1S-E06-02", "M1S-E06-03", "M1S-E06-05"), async () => {
  await mia.getByRole("button", { name: `Deactivate ${MIA.displayName}` }).click();
  await mia.getByRole("alertdialog", { name: `Deactivate ${MIA.displayName}?` }).getByRole("button", { name: "Deactivate" })
    .click();
  await expect(mia.getByRole("alert").filter({ hasText: LAST_OWNER })).toBeVisible();

  await mia.getByRole("button", { name: `Edit ${MIA.displayName}` }).click();
  const edit = mia.getByRole("dialog", { name: "Edit member" });
  await chooseOption(mia, "Role", "Adult");
  await edit.getByRole("button", { name: "Save" }).click();
  await expect(mia.getByRole("alert").filter({ hasText: LAST_OWNER })).toBeVisible();
  await mia.keyboard.press("Escape");
  const row = mia.getByRole("list", { name: "Members" }).getByRole("listitem").filter({ hasText: "mia" });
  await expect(row).toContainText("Owner");
  await expect(row).not.toContainText("Deactivated");
});

test("10 · household name and time zone", story(DEMO, "M1S-E04-02", "M1S-E04-03", "M1S-E04-04"), async () => {
  await openSettings(mia, "Household");
  await mia.getByRole("textbox", { name: "Household name" }).fill("Familie Müller-Schmidt");
  await chooseOption(mia, "Time zone", KIRITIMATI);
  await mia.getByRole("button", { name: "Save household" }).click();
  await expect(mia.getByText("Household saved")).toBeVisible();
  await expect(mia).toHaveTitle("Household · Familie Müller-Schmidt");

  const api = await Api.login(MIA.user, MIA.password, FRESH_URL);
  try {
    await api.createTask("Due today in Kiritimati", isoDateIn(KIRITIMATI, 0));
    await api.createTask("Due yesterday in Kiritimati", isoDateIn(KIRITIMATI, -1));
  } finally {
    await api.dispose();
  }
  await goNav(mia, "Today");
  const widget = ui.tasksWidget(mia);
  await expect(ui.row(widget, "Due today in Kiritimati")).toContainText("Today");
  await expect(ui.row(widget, "Due yesterday in Kiritimati")).toContainText("Overdue");
  await expect(mia).toHaveTitle("Today · Familie Müller-Schmidt");
});

test("11 · an ended session sends you back to where you were", story(DEMO, "M1S-E07-03", "M1S-E05-02"), async () => {
  const other = await Api.login(MIA.user, MIA.password, FRESH_URL);
  try {
    await other.logoutEverywhere();
  } finally {
    await other.dispose();
  }
  await ui.addTask(mia).fill("After the session ended");
  await ui.addTask(mia).press("Enter");
  await expect(mia).toHaveURL(/\/login\?.*reason=expired/);
  await expect(mia.getByText(SESSION_ENDED)).toBeVisible();
  await signIn(mia, MIA.user, MIA.password);
  await expect(mia).toHaveURL(/\/today$/);
});
