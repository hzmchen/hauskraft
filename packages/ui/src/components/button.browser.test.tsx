// SPDX-License-Identifier: MIT
// Real-browser check: the button's colours come from theme tokens (CSS variables), not literals.
import { render } from "@testing-library/react";
import { expect, it } from "vitest";

import "../styles.css";
import "../tokens/fallback.css";
import { Button } from "../index";

it("paints the primary button with the theme's primary token", () => {
  const { getByRole } = render(<Button>Save</Button>);
  const style = getComputedStyle(getByRole("button", { name: "Save" }));
  const primary = getComputedStyle(document.documentElement).getPropertyValue("--hauskraft-color-primary").trim();
  expect(primary).not.toBe("");
  expect(style.backgroundColor.replace(/,\s*/g, " ")).toContain(primary.replace(/^rgb\(|\)$/g, ""));
});
