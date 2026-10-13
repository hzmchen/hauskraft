// SPDX-License-Identifier: AGPL-3.0-or-later
import { createFileRoute } from "@tanstack/react-router";
import { useId } from "react";
import { useTranslation } from "react-i18next";

import { ColorModeControl } from "../../shell/ColorMode";

export const Route = createFileRoute("/_app/settings/appearance")({ component: Appearance });

// The household theme picker joins with M0S-E13-07.
function Appearance() {
  const { t } = useTranslation();
  const deviceId = useId();
  return (
    <div className="flex flex-col gap-density">
      <h1 className="text-2xl font-bold">{t("settings.appearance")}</h1>
      <section aria-labelledby={deviceId} className="flex flex-col gap-2">
        <h2 id={deviceId} className="text-lg font-bold">
          {t("settings.this_device")}
        </h2>
        <p className="text-muted-foreground">{t("settings.this_device_hint")}</p>
        <ColorModeControl />
      </section>
    </div>
  );
}
