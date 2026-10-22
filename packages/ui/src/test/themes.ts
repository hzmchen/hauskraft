// SPDX-License-Identifier: MIT
// Test helper: apply a built-in theme's compiled stylesheet (the reviewed golden files) and its variant
// attributes to <html>, as the shell does at runtime (M0S-E13-05).
import defaultCss from "../../../../services/core_api/tests/unit/golden/builtin-default.css?raw";
import hackspaceCss from "../../../../services/core_api/tests/unit/golden/builtin-hackspace.css?raw";
import paperCss from "../../../../services/core_api/tests/unit/golden/builtin-paper.css?raw";

export const THEMES = { default: defaultCss, paper: paperCss, hackspace: hackspaceCss } as const;
export type ThemeName = keyof typeof THEMES;

export function applyTheme(name: ThemeName, attributes: Record<string, string> = {}, dark = false): void {
  let style = document.getElementById("hauskraft-theme-under-test");
  if (!style) {
    style = document.createElement("style");
    style.id = "hauskraft-theme-under-test";
    document.head.append(style);
  }
  // Fonts are served by the API; tests use the fallback stacks.
  style.textContent = THEMES[name].replace(/^@font-face.*$/gm, "");
  const html = document.documentElement;
  for (const attr of [...html.attributes]) if (attr.name.startsWith("data-hauskraft-")) html.removeAttribute(attr.name);
  for (const [key, value] of Object.entries(attributes)) html.setAttribute(`data-hauskraft-${key}`, value);
  html.classList.toggle("dark", dark);
}

export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** Normalise a computed colour ("1, 2, 3" vs "1 2 3" separators) for comparisons. */
export function sameColour(value: string): string {
  return value.replace(/,\s*/g, " ").replace(/\s+\/\s+1\)$/, ")");
}
