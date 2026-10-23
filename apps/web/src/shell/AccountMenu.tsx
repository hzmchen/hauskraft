// SPDX-License-Identifier: AGPL-3.0-or-later
// The account menu (ui-contract: button "Account menu"; menuitemradio English/Deutsch; menuitems "Account settings"
// (M1S-E08-03) and "Sign out").
// The button shows its name as its label (WCAG 2.5.3, label in name).
import {
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Icon,
} from "@hauskraft/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { LANGUAGES, isLanguage } from "../i18n";
import { useLanguage } from "../i18n/useLanguage";
import { signOut } from "../session";

export function AccountMenu() {
  const { t } = useTranslation();
  const { language, changeLanguage } = useLanguage();
  const queryClient = useQueryClient();
  const router = useRouter();

  async function onSignOut() {
    await signOut(queryClient);
    await router.navigate({ to: "/login" });
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost">
          <Icon name="user.menu" />
          <span>{t("account.menu")}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>{t("account.language")}</DropdownMenuLabel>
        <DropdownMenuRadioGroup
          value={language}
          onValueChange={(value) => isLanguage(value) && void changeLanguage(value)}
        >
          {LANGUAGES.map((lng) => (
            <DropdownMenuRadioItem key={lng} value={lng} lang={lng}>
              {t(`language.${lng}`)}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => void router.navigate({ to: "/settings/account" })}>
          {t("account.settings")}
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => void onSignOut()}>{t("account.sign_out")}</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
