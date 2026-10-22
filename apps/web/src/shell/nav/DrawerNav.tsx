// SPDX-License-Identifier: AGPL-3.0-or-later
import { Button, Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from "@hauskraft/ui";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { NavRendererProps } from "./model";
import { NavLinks } from "./NavLinks";

/** Narrow screens: an "Open menu" button with the navigation in a side sheet. */
export function DrawerNav({ items }: NavRendererProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" aria-label={t("nav.open_menu")}>
          {t("nav.menu_button")}
        </Button>
      </SheetTrigger>
      <SheetContent side="left" closeLabel={t("nav.close_menu")} className="bg-nav text-nav-foreground">
        <SheetTitle className="px-density pt-density">{t("app.name")}</SheetTitle>
        <SheetDescription className="sr-only">{t("nav.label")}</SheetDescription>
        <nav aria-label={t("nav.label")} data-nav-style="drawer" className="p-density">
          <NavLinks items={items} className="flex flex-col gap-1" onNavigate={() => setOpen(false)} />
        </nav>
      </SheetContent>
    </Sheet>
  );
}
