// SPDX-License-Identifier: MIT
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "../index";

describe("Button", () => {
  it("renders a named button with its slot hook", () => {
    render(<Button>Save</Button>);
    const button = screen.getByRole("button", { name: "Save" });
    expect(button.dataset.slot).toBe("button");
  });

  it("keeps role and name for every variant", () => {
    for (const variant of ["default", "destructive", "outline", "secondary", "ghost", "link"] as const) {
      const { unmount } = render(<Button variant={variant}>Delete</Button>);
      expect(screen.getByRole("button", { name: "Delete" })).toBeDefined();
      unmount();
    }
  });
});
