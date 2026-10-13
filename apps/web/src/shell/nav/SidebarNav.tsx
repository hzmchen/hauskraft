// SPDX-License-Identifier: AGPL-3.0-or-later
import { useTranslation } from "react-i18next";

import type { NavRendererProps } from "./model";
import { NavLinks } from "./NavLinks";

/** Wide screens: a column on the left. */
export function SidebarNav({ items }: NavRendererProps) {
  const { t } = useTranslation();
  return (
    <nav
      aria-label={t("nav.label")}
      data-nav-style="sidebar"
      className="w-56 shrink-0 bg-nav p-density text-nav-foreground"
    >
      <NavLinks items={items} className="flex flex-col gap-1" />
    </nav>
  );
}
