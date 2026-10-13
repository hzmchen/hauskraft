// SPDX-License-Identifier: MIT
import { render, screen } from "@testing-library/react";
import { userEvent } from "vitest/browser";
import { afterEach, describe, expect, it } from "vitest";

import "../styles.css";
import { Button, Checkbox } from "../index";
import { applyTheme, cssVar, sameColour, THEMES, type ThemeName } from "../test/themes";

afterEach(() => document.body.replaceChildren());

describe.each(Object.keys(THEMES) as ThemeName[])("variants in %s", (theme) => {
  it.each(["solid", "soft", "outline"])("primary button %s: same role, name and keyboard", async (button) => {
    applyTheme(theme, { button });
    let clicks = 0;
    render(<Button onClick={() => clicks++}>Save</Button>);
    const el = screen.getByRole("button", { name: "Save" });
    await userEvent.unhover(el); // the pointer may still rest where an earlier test's button was
    await userEvent.tab();
    expect(document.activeElement).toBe(el);
    await userEvent.keyboard("{Enter}");
    expect(clicks).toBe(1);
    const bg = sameColour(getComputedStyle(el).backgroundColor);
    if (button === "solid") expect(bg).toBe(sameColour(cssVar("--hearth-color-primary")));
    if (button === "soft") expect(bg).toBe(sameColour(cssVar("--hearth-color-accent")));
    if (button === "outline") expect(getComputedStyle(el).borderTopWidth).not.toBe("0px");
  });

  it.each(["square", "round"])("checkbox %s: same role, name and keyboard", async (checkbox) => {
    applyTheme(theme, { checkbox });
    render(<Checkbox aria-label="Mark 'Milk' as done" />);
    const box = screen.getByRole("checkbox", { name: "Mark 'Milk' as done" });
    await userEvent.tab();
    await userEvent.keyboard(" ");
    expect(box.getAttribute("aria-checked")).toBe("true");
    const radius = parseFloat(getComputedStyle(box).borderTopLeftRadius);
    if (checkbox === "round") expect(radius).toBeGreaterThan(100);
    if (checkbox === "square") expect(radius).toBeLessThan(10);
  });

  it("density scales p-density", () => {
    applyTheme(theme);
    render(<div data-testid="box" className="p-density" />);
    const unit = parseFloat(cssVar("--hearth-space-unit"));
    const density = parseFloat(cssVar("--hearth-density"));
    expect(parseFloat(getComputedStyle(screen.getByTestId("box")).paddingTop)).toBeCloseTo(4 * unit * density, 1);
  });
});
