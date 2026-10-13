// SPDX-License-Identifier: MIT
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Icon, IconProvider, ICON_NAMES } from "../index";

describe("Icon", () => {
  it("falls back to the default pack for every core name, hidden from assistive tech", () => {
    for (const name of ICON_NAMES) {
      const { container, unmount } = render(<Icon name={name} />);
      const svg = container.querySelector("svg")!;
      expect(svg.getAttribute("aria-hidden")).toBe("true");
      expect(svg.querySelector("use")).toBeNull();
      unmount();
    }
  });

  it("uses the theme sprite when the sprite lists the name", () => {
    const { container } = render(
      <IconProvider spriteUrl="/api/v1/theme/assets/x/sprite.svg?h=1" names={["action.add"]}>
        <Icon name="action.add" />
        <Icon name="action.delete" />
      </IconProvider>,
    );
    const [add, del] = container.querySelectorAll("svg");
    expect(add!.querySelector("use")!.getAttribute("href")).toBe("/api/v1/theme/assets/x/sprite.svg?h=1#action.add");
    expect(del!.querySelector("use")).toBeNull();
  });

  it("is an image with a name when labelled", () => {
    const { getByRole } = render(<Icon name="status.overdue" label="Overdue" />);
    expect(getByRole("img", { name: "Overdue" })).toBeDefined();
  });

  it("renders something for unknown names instead of failing", () => {
    const { container } = render(<Icon name="org.example.unknown" />);
    expect(container.querySelector("svg")).not.toBeNull();
  });
});
