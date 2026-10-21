// SPDX-License-Identifier: AGPL-3.0-or-later
// i18n (M0S-E08-04): the `shell` namespace plus one namespace per plugin (PluginWebModule.locales).
// The language lives on this device (localStorage) and in the account (PATCH /me {locale}).
import i18next, { type i18n as I18n } from "i18next";
import { initReactI18next } from "react-i18next";

import de from "./locales/de/shell.json";
import en from "./locales/en/shell.json";

export const LANGUAGES = ["en", "de"] as const;
export type Language = (typeof LANGUAGES)[number];
export const LOCALE_STORAGE_KEY = "hauskraft.locale";

export function isLanguage(value: unknown): value is Language {
  return typeof value === "string" && (LANGUAGES as readonly string[]).includes(value);
}

function storedLanguage(): Language | null {
  try {
    const value = localStorage.getItem(LOCALE_STORAGE_KEY);
    return isLanguage(value) ? value : null;
  } catch {
    return null; // private mode or blocked storage
  }
}

function browserLanguage(): Language {
  const preferred = typeof navigator === "undefined" ? [] : navigator.languages;
  return preferred.some((tag) => tag.toLowerCase().startsWith("de")) ? "de" : "en";
}

/** A ready i18next instance. Resources are bundled, so initialisation is synchronous. */
export function createI18n(options: { lng?: Language } = {}): I18n {
  const instance = i18next.createInstance();
  void instance.use(initReactI18next).init({
    resources: { en: { shell: en }, de: { shell: de } },
    lng: options.lng ?? storedLanguage() ?? browserLanguage(),
    fallbackLng: "en",
    supportedLngs: [...LANGUAGES],
    ns: ["shell"],
    defaultNS: "shell",
    initAsync: false,
    interpolation: { escapeValue: false }, // React escapes
    saveMissing: import.meta.env.DEV,
    missingKeyHandler: (lngs, ns, key) => console.warn(`i18n: missing ${ns}:${key} for ${lngs.join(",")}`),
  });
  return instance;
}

/** Register a plugin's strings under its own namespace. */
export function addPluginLocales(i18n: I18n, namespace: string, locales: Record<Language, object>): void {
  for (const lng of LANGUAGES) i18n.addResourceBundle(lng, namespace, locales[lng], true, true);
}

/** Switch language on this device and save it to the account with `save` (PATCH /me). */
export async function setLanguage(i18n: I18n, lng: Language, save: (lng: Language) => Promise<unknown>) {
  await i18n.changeLanguage(lng);
  document.documentElement.lang = lng;
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, lng);
  } catch {
    // storage unavailable: the choice holds for this session
  }
  await save(lng);
}

/** Dates in the reader's language; `YYYY-MM-DD` is a calendar date, not a UTC instant. */
export function formatDate(value: string | Date, lng: Language): string {
  const date =
    typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)
      ? new Date(Number(value.slice(0, 4)), Number(value.slice(5, 7)) - 1, Number(value.slice(8, 10)))
      : new Date(value);
  return new Intl.DateTimeFormat(lng === "de" ? "de-DE" : "en-US", { dateStyle: "medium" }).format(date);
}
