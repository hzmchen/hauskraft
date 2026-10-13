// SPDX-License-Identifier: AGPL-3.0-or-later
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createI18n, LOCALE_STORAGE_KEY, setLanguage } from "./index";

type Tree = { [key: string]: string | Tree };

function keys(tree: Tree, prefix = ""): string[] {
  return Object.entries(tree).flatMap(([k, v]) =>
    typeof v === "string" ? [`${prefix}${k}`] : keys(v, `${prefix}${k}.`),
  );
}

const shell = import.meta.glob<Tree>("./locales/*/*.json", { eager: true, import: "default" });
const plugins = import.meta.glob<Tree>("../../../../plugins/official/*/web/src/locales/*/*.json", {
  eager: true,
  import: "default",
});

describe("locale files", () => {
  const all = { ...shell, ...plugins };
  const english = Object.keys(all).filter((path) => path.includes("/en/"));

  it("has a shell namespace in English and German", () => {
    expect(Object.keys(shell)).toEqual(expect.arrayContaining(["./locales/en/shell.json", "./locales/de/shell.json"]));
  });

  it.each(english)("%s has the same keys in German, none empty", (path) => {
    const german = all[path.replace("/en/", "/de/")];
    expect(german, `${path} has no German twin`).toBeDefined();
    expect(keys(german!).sort()).toEqual(keys(all[path]!).sort());
    for (const tree of [all[path]!, german!]) {
      const empty = keys(tree).filter(
        (key) => !String(key.split(".").reduce<unknown>((t, k) => (t as Tree)[k], tree)).trim(),
      );
      expect(empty).toEqual([]);
    }
  });
});

describe("runtime", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.unstubAllGlobals());

  it("falls back to English for a key German lacks", async () => {
    const i18n = await createI18n({ lng: "de" });
    i18n.addResource("en", "shell", "test.only_english", "Only English");
    expect(i18n.t("test.only_english")).toBe("Only English");
  });

  it("starts in the stored language", async () => {
    localStorage.setItem(LOCALE_STORAGE_KEY, "de");
    const i18n = await createI18n();
    expect(i18n.language).toBe("de");
    expect(i18n.t("nav.today")).toBe("Heute");
  });

  it("switching language stores it on this device and saves it to the account", async () => {
    const i18n = await createI18n({ lng: "en" });
    const save = vi.fn(async () => undefined);
    await setLanguage(i18n, "de", save);
    expect(i18n.language).toBe("de");
    expect(localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("de");
    expect(save).toHaveBeenCalledWith("de");
  });

  it("still switches when storage is unavailable", async () => {
    const i18n = await createI18n({ lng: "en" });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });
    await setLanguage(i18n, "de", async () => undefined);
    expect(i18n.language).toBe("de");
    vi.restoreAllMocks();
  });

  it("formats dates per language", async () => {
    const { formatDate } = await import("./index");
    expect(formatDate("2026-10-13", "de")).toBe("13.10.2026");
    expect(formatDate("2026-10-13", "en")).toMatch(/Oct(ober)? 13, 2026/);
  });
});
