// SPDX-License-Identifier: AGPL-3.0-or-later
import { QueryClient } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./app";
import { createI18n } from "./i18n";
import { createAppRouter } from "./router";
import { fakeApi, problem } from "./test/fakeApi";

afterEach(() => vi.unstubAllGlobals());

describe("shell", () => {
  it("renders inside a main landmark", async () => {
    fakeApi({ "GET /api/v1/auth/session": () => problem(401, "unauthenticated") });
    const queryClient = new QueryClient();
    render(
      <App
        router={createAppRouter({ initialPath: "/", queryClient, i18n: createI18n({ lng: "en" }) })}
        queryClient={queryClient}
      />,
    );
    expect(await screen.findByRole("main")).toBeDefined();
  });
});
