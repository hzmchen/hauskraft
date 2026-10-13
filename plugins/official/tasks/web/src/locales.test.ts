// SPDX-License-Identifier: MIT
import i18next from "i18next";
import { describe, expect, it } from "vitest";

import de from "./locales/de/tasks.json";
import en from "./locales/en/tasks.json";
import plugin from "./index";

async function t(lng: "en" | "de") {
  const i18n = i18next.createInstance();
  await i18n.init({ lng, resources: { en: { tasks: en }, de: { tasks: de } }, defaultNS: "tasks" });
  return i18n.t.bind(i18n);
}

describe("tasks locales", () => {
  it("the web module ships the JSON namespaces", () => {
    expect(plugin.locales).toEqual({ en, de });
  });

  it("counts open tasks with plural forms", async () => {
    const english = await t("en");
    expect(english("open_count", { count: 1 })).toBe("1 open");
    expect(english("open_count", { count: 3 })).toBe("3 open");
    const german = await t("de");
    expect(german("open_count", { count: 1 })).toBe("1 offen");
    expect(german("widget.title")).toBe("Aufgaben");
  });
});
