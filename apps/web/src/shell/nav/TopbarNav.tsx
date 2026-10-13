// SPDX-License-Identifier: AGPL-3.0-or-later
import { useTranslation } from "react-i18next";

import type { NavRendererProps } from "./model";
import { NavLinks } from "./NavLinks";

/** Wide screens: a row in the header. */
export function TopbarNav({ items }: NavRendererProps) {
  const { t } = useTranslation();
  return (
    <nav aria-label={t("nav.label")} data-nav-style="topbar" className="min-w-0">
      <NavLinks items={items} className="flex flex-wrap items-center gap-1" />
    </nav>
  );
}
