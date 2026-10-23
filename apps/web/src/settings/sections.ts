// SPDX-License-Identifier: AGPL-3.0-or-later
// The settings sections (M1S-E08-01, spec §10.1): one model, filtered by the session's permissions (never by role
// names or the theme), so every theme shows the same sections to the same role.

export interface SettingsSection {
  id: string;
  /** i18n key of the section name, which is also its page's level-1 heading. */
  labelKey: string;
  href: "/settings/appearance" | "/settings/account" | "/settings/household" | "/settings/members";
  /** The permission the section needs; none means everyone. */
  requires?: string;
}

export const SETTINGS_SECTIONS: readonly SettingsSection[] = [
  { id: "appearance", labelKey: "settings.appearance", href: "/settings/appearance" },
  { id: "account", labelKey: "settings.account", href: "/settings/account" },
  { id: "household", labelKey: "settings.household", href: "/settings/household", requires: "settings.household.set" },
  { id: "members", labelKey: "settings.members", href: "/settings/members", requires: "user.list" },
];

export function visibleSections(permissions: readonly string[]): SettingsSection[] {
  return SETTINGS_SECTIONS.filter((section) => !section.requires || permissions.includes(section.requires));
}

/** For an owner-only route's `beforeLoad`: true when the session may open the section with this id. */
export function mayOpen(id: string, permissions: readonly string[]): boolean {
  return visibleSections(permissions).some((section) => section.id === id);
}
