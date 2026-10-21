// SPDX-License-Identifier: AGPL-3.0-or-later
// Settings → Appearance (M0S-E13-07): the household theme (everyone, every device) and this device's
// colour mode. Choosing a theme asks first. No editor and no free-form input.
import {
  settingsThemeSetMutation,
  themesActiveQueryKey,
  themesListOptions,
  themesListQueryKey,
  type ThemeSummary,
} from "@hauskraft/sdk-ts";
import { Button, Dialog, DialogContent, DialogDescription, DialogFooter, DialogTitle, Swatch, cn } from "@hauskraft/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { ColorModeControl } from "../shell/ColorMode";

export const THEMES_GUIDE_URL = "https://github.com/hzmchen/hauskraft/blob/main/docs/themes.md";

export function AppearanceSettings() {
  const { t } = useTranslation();
  const ids = { household: useId(), hint: useId(), device: useId() };
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">{t("settings.appearance")}</h1>
      <section aria-labelledby={ids.household} className="flex flex-col gap-3">
        <h2 id={ids.household} className="text-lg font-bold">
          {t("settings.household_theme")}
        </h2>
        <p id={ids.hint} className="text-muted-foreground">
          {t("settings.household_hint")}
        </p>
        <ThemePicker labelledBy={ids.household} describedBy={ids.hint} />
        <p>
          <a href={THEMES_GUIDE_URL} target="_blank" rel="noreferrer noopener" className="text-primary underline">
            {t("settings.add_theme")}
          </a>
        </p>
      </section>
      <section aria-labelledby={ids.device} className="flex flex-col gap-2">
        <h2 id={ids.device} className="text-lg font-bold">
          {t("settings.this_device")}
        </h2>
        <p className="text-muted-foreground">{t("settings.this_device_hint")}</p>
        <ColorModeControl />
      </section>
    </div>
  );
}

function ThemePicker({ labelledBy, describedBy }: { labelledBy: string; describedBy: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data } = useQuery(themesListOptions());
  // Built-in themes first, then other usable ones, then the ones that can't be used; by name within each.
  const rank = (theme: ThemeSummary) => (!theme.valid ? 2 : theme.origin === "builtin" ? 0 : 1);
  const themes = [...(data ?? [])].sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name));
  const [pending, setPending] = useState<ThemeSummary | null>(null);
  const save = useMutation({
    ...settingsThemeSetMutation(),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: themesListQueryKey() }),
        queryClient.invalidateQueries({ queryKey: themesActiveQueryKey() }),
      ]);
    },
  });
  const active = themes.find((theme) => theme.active)?.theme_id;
  const checked = pending?.theme_id ?? active;
  const name = useId();

  return (
    <>
      <div
        role="radiogroup"
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"
      >
        {themes.map((theme) => (
          <ThemeCard
            key={theme.theme_id}
            theme={theme}
            group={name}
            checked={checked === theme.theme_id}
            onChoose={() => theme.theme_id !== active && setPending(theme)}
          />
        ))}
      </div>
      <Dialog open={pending !== null} onOpenChange={(open) => !open && setPending(null)}>
        <DialogContent showCloseButton={false}>
          <DialogTitle>{t("settings.confirm_title")}</DialogTitle>
          <DialogDescription>{t("settings.confirm_body", { name: pending?.name ?? "" })}</DialogDescription>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPending(null)}>
              {t("settings.cancel")}
            </Button>
            <Button
              disabled={save.isPending}
              onClick={async () => {
                if (pending) await save.mutateAsync({ body: { theme_id: pending.theme_id } });
                setPending(null);
              }}
            >
              {t("settings.confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

function ThemeCard({
  theme,
  group,
  checked,
  onChoose,
}: {
  theme: ThemeSummary;
  group: string;
  checked: boolean;
  onChoose: () => void;
}) {
  const { t } = useTranslation();
  const ids = { name: useId(), details: useId(), problems: useId() };
  const [showProblems, setShowProblems] = useState(false);
  const { preview } = theme;
  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-lg border bg-widget p-density text-widget-foreground",
        checked && "border-primary ring-2 ring-ring",
        // Not faded: dimming would push its text below the contrast minimum. Dashed border + message instead.
        !theme.valid && "border-dashed",
      )}
    >
      <label className="flex items-center gap-2">
        <input
          type="radio"
          name={group}
          checked={checked}
          disabled={!theme.valid}
          onChange={onChoose}
          aria-labelledby={ids.name}
          aria-describedby={ids.details}
          className="size-4 accent-primary"
        />
        {/* Theme names are proper nouns from the theme; they are not translated. */}
        <span id={ids.name} className="font-bold">
          {theme.name}
        </span>
        {theme.active ? (
          // Visual only: the checked radio already tells assistive tech which theme is active.
          <span aria-hidden="true" className="ml-auto rounded-full bg-primary px-2 text-xs text-primary-foreground">
            {t("settings.active")}
          </span>
        ) : null}
      </label>
      <div id={ids.details} className="flex flex-col gap-2 text-sm">
        <span className="text-muted-foreground">
          {t("settings.by", { authors: theme.authors.join(", ") })} ·{" "}
          {t("settings.version", { version: theme.version })}
        </span>
        <span className="flex flex-wrap items-center gap-1">
          <span className="text-muted-foreground">{t("mode.light")}</span>
          {preview.swatches.light.map((color, i) => (
            <Swatch key={`l${i}`} color={color} />
          ))}
          <span className="ml-2 text-muted-foreground">{t("mode.dark")}</span>
          {preview.swatches.dark.map((color, i) => (
            <Swatch key={`d${i}`} color={color} />
          ))}
        </span>
        {preview.navigation.wide && preview.density ? (
          <span className="flex flex-wrap gap-1 text-xs">
            <span className="rounded-sm bg-muted px-1.5 text-muted-foreground">
              {t("settings.navigation", {
                wide: t(`settings.nav_style.${preview.navigation.wide}`, { defaultValue: preview.navigation.wide }),
                narrow: t(`settings.nav_style.${preview.navigation.narrow}`, {
                  defaultValue: preview.navigation.narrow,
                }),
              })}
            </span>
            <span className="rounded-sm bg-muted px-1.5 text-muted-foreground">
              {t("settings.density", {
                density: t(`settings.density_value.${preview.density}`, { defaultValue: preview.density }),
              })}
            </span>
          </span>
        ) : null}
      </div>
      {!theme.valid ? (
        <div className="flex flex-col gap-1 text-sm">
          <span className="text-destructive">{t("settings.invalid")}</span>
          <Button
            variant="outline"
            size="sm"
            aria-expanded={showProblems}
            aria-controls={ids.problems}
            onClick={() => setShowProblems((shown) => !shown)}
            className="self-start"
          >
            {t("settings.show_problems")}
          </Button>
          {showProblems ? (
            <ul id={ids.problems} className="list-disc pl-5">
              {theme.errors.map((issue, i) => (
                <li key={i}>
                  {issue.message} <code className="font-mono text-xs">{issue.path}</code>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
