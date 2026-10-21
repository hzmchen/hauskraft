// SPDX-License-Identifier: AGPL-3.0-or-later
import { Button, Sheet, SheetContent, SheetDescription, SheetTitle } from "@hauskraft/ui";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { NavRendererProps } from "./model";
import { NavLinks } from "./NavLinks";

const MAX_TABS = 5;

/**
 * Narrow screens: tabs along the bottom edge. At most five; with more items the fifth becomes "More",
 * which opens the rest in model order.
 */
export function BottomTabsNav({ items }: NavRendererProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const overflow = items.length > MAX_TABS;
  const tabs = overflow ? items.slice(0, MAX_TABS - 1) : items;
  const rest = overflow ? items.slice(MAX_TABS - 1) : [];
  return (
    <nav
      aria-label={t("nav.label")}
      data-nav-style="bottom-tabs"
      className="fixed inset-x-0 bottom-0 z-40 flex items-stretch border-t bg-nav text-nav-foreground"
    >
      <NavLinks
        items={tabs}
        className="flex flex-1 items-stretch justify-around"
        itemClassName="flex-col gap-1 px-2 py-2 text-xs"
      />
      {overflow ? (
        <Sheet open={open} onOpenChange={setOpen}>
          <Button variant="ghost" className="h-auto flex-col text-xs" onClick={() => setOpen(true)}>
            {t("nav.more")}
          </Button>
          <SheetContent side="bottom" closeLabel={t("nav.close_menu")} className="bg-nav text-nav-foreground">
            <SheetTitle className="px-density pt-density">{t("nav.more")}</SheetTitle>
            <SheetDescription className="sr-only">{t("nav.label")}</SheetDescription>
            <NavLinks items={rest} className="flex flex-col gap-1 p-density" onNavigate={() => setOpen(false)} />
          </SheetContent>
        </Sheet>
      ) : null}
    </nav>
  );
}
