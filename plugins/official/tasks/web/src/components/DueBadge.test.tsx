// SPDX-License-Identifier: MIT
import { HostProvider, type Host } from "@hauskraft/sdk-ts";
import { screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { todayIso } from "../api";
import { renderWithPlugin } from "../test/harness";
import { DueBadge } from "./DueBadge";

// 2026-11-02 23:30 in Berlin is already 2026-11-03 12:30 in Kiritimati (UTC+14).
const NOW = new Date("2026-11-02T23:30:00+01:00");

function host(timeZone: string): Host {
  return { navigate: () => undefined, search: {}, setSearch: () => undefined, timeZone };
}

beforeEach(() => vi.useFakeTimers({ now: NOW, toFake: ["Date"] }));
afterEach(() => vi.useRealTimers());

describe("DueBadge in the household time zone (M1S-E04-03)", () => {
  it("counts today in the household's zone, not the browser's", async () => {
    await renderWithPlugin(
      <HostProvider host={host("Pacific/Kiritimati")}>
        <ul>
          <li data-testid="today">
            <DueBadge due="2026-11-03" done={false} />
          </li>
          <li data-testid="yesterday">
            <DueBadge due="2026-11-02" done={false} />
          </li>
        </ul>
      </HostProvider>,
    );
    expect(screen.getByTestId("today").textContent).toContain("Today");
    expect(screen.getByTestId("yesterday").textContent).toContain("Overdue");
  });

  it("follows another zone just the same", async () => {
    await renderWithPlugin(
      <HostProvider host={host("America/Los_Angeles")}>
        <span data-testid="badge">
          <DueBadge due="2026-11-02" done={false} />
        </span>
      </HostProvider>,
    );
    expect(screen.getByTestId("badge").textContent).toContain("Today");
  });
});

describe("todayIso", () => {
  it("formats the calendar date in a time zone", () => {
    expect(todayIso(NOW, "Pacific/Kiritimati")).toBe("2026-11-03");
    expect(todayIso(NOW, "Europe/Berlin")).toBe("2026-11-02");
    expect(todayIso(NOW, "America/Los_Angeles")).toBe("2026-11-02");
  });
});
