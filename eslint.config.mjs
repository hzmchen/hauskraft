// SPDX-License-Identifier: AGPL-3.0-or-later
// ESLint 9 flat config for every TypeScript package in the pnpm workspace (M0S-E01-03).
import css from "@eslint/css";
import js from "@eslint/js";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

import hearthos from "./tools/eslint-plugin-hearthos/index.js";

const SCRIPTS = ["**/*.{js,mjs,cjs,ts,tsx,mts,cts}"];

// UI code that must use theme tokens only (AGPL rule 11, M0S-E13-08).
const UI_SOURCES = ["apps/web/src", "packages/ui/src", "plugins/**/web/src"];

// Plugin web code may import only these packages (spec §4.2 licence boundary, AGENTS.md rule 2).
const PLUGIN_WEB_ALLOWED = [
  "@hearthos/sdk-ts",
  "@hearthos/ui",
  "react",
  "react-dom",
  "react-i18next",
  "@tanstack/react-query",
];
const escape = (s) => s.replace(/[.*+?^${}()|[\]\\/]/g, "\\$&");
const allowed = PLUGIN_WEB_ALLOWED.map(escape).join("|");

export default tseslint.config(
  {
    ignores: [
      "**/node_modules/**",
      "**/.venv/**",
      "**/dist/**",
      "**/*.gen.ts",
      "packages/sdk-ts/src/client/**",
      // Spec-owned acceptance suite and its fixtures keep their own style.
      "tests/**",
    ],
  },
  // JS/TS presets apply to script files only; CSS has its own language block below.
  { files: SCRIPTS, ...js.configs.recommended },
  ...tseslint.configs.recommended.map((config) => ({ files: SCRIPTS, ...config })),
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: { globals: { ...globals.browser } },
    plugins: { "react-hooks": reactHooks, "jsx-a11y": jsxA11y },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.flatConfigs.recommended.rules,
    },
  },
  {
    files: ["plugins/**/web/src/**/*.{ts,tsx}"],
    ignores: ["**/*.test.{ts,tsx}", "**/test/**"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              regex: "(^|/)apps/web(/|$)",
              message: "Plugins may not import the app shell; use @hearthos/sdk-ts and @hearthos/ui.",
            },
            {
              regex: `^(?!\\.{1,2}/)(?!(${allowed})(/|$))`,
              message: `Plugin web code may import only ${PLUGIN_WEB_ALLOWED.join(", ")} and its own files.`,
            },
          ],
        },
      ],
    },
  },
  {
    files: ["**/*.{js,mjs,cjs}"],
    languageOptions: { globals: { ...globals.node } },
  },
  {
    files: UI_SOURCES.map((root) => `${root}/**/*.{ts,tsx}`),
    plugins: { hearthos },
    rules: { "hearthos/no-raw-styles": "error" },
  },
  {
    files: UI_SOURCES.map((root) => `${root}/**/*.css`),
    // The Default theme's values, generated from themes/builtin/default (the one place for literals).
    ignores: ["packages/ui/src/tokens/fallback.css"],
    language: "css/css",
    languageOptions: { tolerant: true }, // Tailwind at-rules (@theme, @utility, @custom-variant, …)
    plugins: { css, hearthos },
    rules: { "hearthos/no-raw-styles": "error" },
  },
);
