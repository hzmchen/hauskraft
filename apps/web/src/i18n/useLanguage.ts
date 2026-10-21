// SPDX-License-Identifier: AGPL-3.0-or-later
import { usersMeUpdate } from "@hauskraft/sdk-ts";
import { useTranslation } from "react-i18next";

import { isLanguage, setLanguage, type Language } from "./index";

/** Current language and a setter that also saves it to the signed-in account. */
export function useLanguage(): { language: Language; changeLanguage: (lng: Language) => Promise<void> } {
  const { i18n } = useTranslation();
  const language = isLanguage(i18n.resolvedLanguage) ? i18n.resolvedLanguage : "en";
  return {
    language,
    changeLanguage: (lng) =>
      setLanguage(i18n, lng, async (locale) => {
        await usersMeUpdate({ body: { locale } }); // signed out: 401, the device choice still applies
      }),
  };
}
