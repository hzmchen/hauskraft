// SPDX-License-Identifier: AGPL-3.0-or-later
import { Icon, cn } from "@hearthos/ui";
import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import type { NavItem } from "./model";

/** The model's items as links, in model order. Renderers choose only the layout. */
export function NavLinks({
  items,
  className,
  itemClassName,
  onNavigate,
}: {
  items: NavItem[];
  className?: string;
  itemClassName?: string;
  onNavigate?: () => void;
}) {
  const { t } = useTranslation();
  return (
    <ul className={className}>
      {items.map((item) => (
        <li key={item.id}>
          <Link
            // Hrefs come from the model (core routes and /p/<page>), not from the typed route tree.
            to={item.href as "/"}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-2 rounded-md px-3 py-2 text-nav-foreground hover:bg-accent hover:text-accent-foreground current-page:bg-nav-active current-page:text-nav-active-foreground",
              itemClassName,
            )}
          >
            <Icon name={item.icon} />
            <span>{t(item.labelKey)}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
