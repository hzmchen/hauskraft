// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it } from "vitest";

import { DEMO_SESSION, OWNER_SESSION } from "../test/fakeApi";
import { SETTINGS_SECTIONS, visibleSections } from "./sections";

describe("settings sections (M1S-E08-01, M2S-E07-01)", () => {
  it("are Appearance, Account, Household, Members, Assistant in this order", () => {
    expect(SETTINGS_SECTIONS.map((s) => s.href)).toEqual([
      "/settings/appearance",
      "/settings/account",
      "/settings/household",
      "/settings/members",
      "/settings/assistant",
    ]);
  });

  it("follow the session's permissions, not role names", () => {
    expect(visibleSections(OWNER_SESSION.permissions).map((s) => s.id)).toEqual([
      "appearance",
      "account",
      "household",
      "members",
      "assistant",
    ]);
    expect(visibleSections(DEMO_SESSION.permissions).map((s) => s.id)).toEqual(["appearance", "account"]);
    expect(visibleSections(["user.list"]).map((s) => s.id)).toEqual(["appearance", "account", "members"]);
  });
});
