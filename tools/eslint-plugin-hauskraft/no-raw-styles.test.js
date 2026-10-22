// SPDX-License-Identifier: MIT
// Unit tests for hauskraft/no-raw-styles (M0S-E13-08). Run: pnpm --filter eslint-plugin-hauskraft test
import css from "@eslint/css";
import { RuleTester } from "eslint";
import tseslint from "typescript-eslint";

import plugin from "./index.js";

const rule = plugin.rules["no-raw-styles"];

const tsx = new RuleTester({
  languageOptions: { parser: tseslint.parser, parserOptions: { ecmaFeatures: { jsx: true } } },
});

tsx.run("no-raw-styles (TS/TSX)", rule, {
  valid: [
    `const a = <div className="bg-surface text-surface-foreground p-density rounded-lg border-border" />;`,
    `const b = <a href="#content">skip</a>;`,
    `const c = <span style={{ "--swatch": color }} />;`,
    `const d = "rgb(1 2 3)"; // hauskraft-allow-raw-style: theme data`,
    `import x from "./bg-red-500.js";`,
    `const e = cn("state-open:animate-in", active && "bg-primary text-primary-foreground");`,
  ],
  invalid: [
    {
      code: `const a = <div style={{ color: "#ff0000" }} />;`,
      errors: [{ messageId: "inlineStyle" }, { messageId: "colourLiteral" }],
    },
    {
      code: `const a = <div style={{ padding: 12, fontFamily: "Comic Sans MS" }} />;`,
      errors: [{ messageId: "inlineStyle" }, { messageId: "inlineStyle" }],
    },
    { code: `const a = <div className="bg-red-500 text-slate-700" />;`, errors: [{ messageId: "paletteClass" }] },
    { code: `const a = <div className="text-white" />;`, errors: [{ messageId: "paletteClass" }] },
    { code: `const a = <div className="p-[13px] bg-[#fff]" />;`, errors: [{ messageId: "arbitraryValue" }] },
    { code: "const a = `ring-[3px] ${x}`;", errors: [{ messageId: "arbitraryValue" }] },
    { code: `const a = "oklch(0.6 0.1 250)";`, errors: [{ messageId: "colourLiteral" }] },
    { code: `const a = { background: "rebeccapurple" };`, errors: [{ messageId: "colourLiteral" }] },
  ],
});

const cssTester = new RuleTester({ plugins: { css }, language: "css/css" });

cssTester.run("no-raw-styles (CSS)", rule, {
  valid: [
    `.a { color: var(--foreground); background: transparent; border-color: currentColor; }`,
    `.b { max-width: 72rem; opacity: 0.2; }`,
  ],
  invalid: [
    { code: `.a { color: #fff; }`, errors: [{ messageId: "colourLiteral" }] },
    { code: `.a { background: rgb(0 0 0 / 50%); }`, errors: [{ messageId: "colourLiteral" }] },
    { code: `.a { color: red; }`, errors: [{ messageId: "colourLiteral" }] },
  ],
});
