// SPDX-License-Identifier: MIT
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import "../styles.css";
import { Button, WidgetFrame } from "../index";
import { applyTheme, cssVar, sameColour, THEMES, type ThemeName } from "../test/themes";

const CHROMES = ["flat", "outlined", "elevated", "tinted"] as const;
const HEADERS = ["inline", "banner"] as const;

afterEach(() => document.body.replaceChildren());

describe.each(Object.keys(THEMES) as ThemeName[])("WidgetFrame in %s", (theme) => {
  it.each(CHROMES.flatMap((chrome) => HEADERS.map((header) => [chrome, header] as const)))(
    "%s chrome with %s header keeps its region, heading and actions",
    (chrome, header) => {
      applyTheme(theme, { chrome, header });
      render(
        <WidgetFrame title="Tasks" actions={<Button variant="ghost">All tasks</Button>}>
          <p>body</p>
        </WidgetFrame>,
      );
      const region = screen.getByRole("region", { name: "Tasks" });
      expect(screen.getByRole("heading", { level: 2, name: "Tasks" })).toBeDefined();
      expect(screen.getByRole("button", { name: "All tasks" })).toBeDefined();
      const style = getComputedStyle(region);
      if (chrome === "outlined") expect(style.borderTopWidth).not.toBe("0px");
      if (chrome === "elevated") expect(style.boxShadow).not.toBe("none");
      if (chrome === "tinted")
        expect(sameColour(style.backgroundColor)).toBe(sameColour(cssVar("--hearth-color-secondary")));
      const bar = region.querySelector("[data-slot=widget-header]")!;
      if (header === "banner") {
        expect(sameColour(getComputedStyle(bar).backgroundColor)).toBe(sameColour(cssVar("--hearth-color-primary")));
      }
    },
  );
});
