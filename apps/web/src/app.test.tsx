// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./app";
import { createAppRouter } from "./router";

describe("shell", () => {
  it("renders the root route inside a main landmark", async () => {
    render(<App router={createAppRouter({ initialPath: "/" })} />);
    expect(await screen.findByRole("main")).toBeDefined();
  });
});
