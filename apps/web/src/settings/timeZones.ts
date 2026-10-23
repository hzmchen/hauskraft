// SPDX-License-Identifier: AGPL-3.0-or-later
// IANA time zone names for the household and setup forms, named by their id (ui-contract). The browser's list
// lacks a few aliases the server accepts (UTC, for one), so the current value is always offered too.

export function timeZoneOptions(current?: string): { value: string; label: string }[] {
  const zones = new Set(Intl.supportedValuesOf("timeZone"));
  if (current) zones.add(current);
  return [...zones].sort().map((zone) => ({ value: zone, label: zone }));
}

export function browserTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}
