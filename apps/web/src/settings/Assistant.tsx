// SPDX-License-Identifier: AGPL-3.0-or-later
// Settings → Assistant (M2S-E07-01..03, owners): the model endpoint with its connection test, tool switches and token
// usage. The API key is write-only: the page only ever shows its last four characters.
import {
  assistantSettingsReadOptions,
  assistantSettingsReadQueryKey,
  assistantSettingsRemoveChat,
  assistantSettingsTest,
  assistantSettingsUpdate,
  assistantStatusQueryKey,
  assistantToolsListOptions,
  assistantToolsListQueryKey,
  assistantUsageReadOptions,
  type AssistantSettings as Settings,
  type ConnectionTest,
  type ToolInfo,
  type UsageGroup,
} from "@hauskraft/sdk-ts";
import { Button, Dialog, DialogContent, DialogDescription, DialogFooter, DialogTitle, cn } from "@hauskraft/ui";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { problemCode, SelectField, TextField } from "../forms/fields";

export function AssistantSettings() {
  const { t } = useTranslation();
  const { data } = useQuery(assistantSettingsReadOptions());
  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-2xl font-bold">{t("settings.assistant")}</h1>
      {data ? <Endpoint settings={data} /> : null}
      {data ? <Tools /> : null}
      {data ? <UsageSection settings={data} /> : null}
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section aria-label={label} className="flex max-w-2xl flex-col gap-3">
      <h2 className="text-xl font-semibold">{label}</h2>
      {children}
    </section>
  );
}

// ---------------------------------------------------------------- M2S-E07-01
function Endpoint({ settings }: { settings: Settings }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const chat = settings.chat;
  const [values, setValues] = useState({
    base_url: chat.base_url ?? "",
    model: chat.model ?? "",
    api_key: "",
    locality: chat.locality,
  });
  const [errors, setErrors] = useState<{ base_url?: string; form?: string }>({});
  const [saved, setSaved] = useState(false);
  const [test, setTest] = useState<ConnectionTest | null>(null);
  const [testing, setTesting] = useState(false);
  const [removing, setRemoving] = useState(false);

  async function refresh() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: assistantSettingsReadQueryKey() }),
      queryClient.invalidateQueries({ queryKey: assistantStatusQueryKey() }),
    ]);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaved(false);
    const body = {
      chat: {
        base_url: values.base_url.trim(),
        model: values.model.trim(),
        locality: values.locality,
        ...(values.api_key ? { api_key: values.api_key } : {}),
      },
    };
    const { data, error } = await assistantSettingsUpdate({ body });
    if (error || !data) {
      setErrors(
        problemCode(error) === "invalid_base_url"
          ? { base_url: t("assistant_page.invalid_base_url") }
          : { form: t("errors.generic") },
      );
      return;
    }
    setErrors({});
    setValues((v) => ({ ...v, api_key: "" }));
    queryClient.setQueryData(assistantSettingsReadQueryKey(), data);
    await queryClient.invalidateQueries({ queryKey: assistantStatusQueryKey() });
    setSaved(true);
  }

  async function runTest() {
    setTesting(true);
    setTest(null);
    const { data } = await assistantSettingsTest();
    setTest(data ?? null);
    setTesting(false);
  }

  async function remove() {
    await assistantSettingsRemoveChat();
    setRemoving(false);
    setValues({ base_url: "", model: "", api_key: "", locality: "cloud" });
    setTest(null);
    await refresh();
  }

  const checks: [keyof ConnectionTest["checks"], string][] = [
    ["reachable", "check_reachable"],
    ["auth", "check_auth"],
    ["model", "check_model"],
    ["tool_calls", "check_tool_calls"],
  ];
  const keyHint =
    chat.api_key_status === "needs_reentry"
      ? t("assistant_page.needs_reentry")
      : chat.api_key_hint
        ? `${t("assistant_page.api_key_saved", { hint: chat.api_key_hint.replace("…", "") })}. ${t("assistant_page.api_key_keep")}`
        : undefined;
  return (
    <Section label={t("assistant_page.endpoint")}>
      <form onSubmit={save} className="flex flex-col gap-3">
        <TextField
          label={t("assistant_page.base_url")}
          hint={t("assistant_page.base_url_hint")}
          value={values.base_url}
          onChange={(event) => setValues((v) => ({ ...v, base_url: event.target.value }))}
          error={errors.base_url}
          required
          maxLength={500}
          autoComplete="off"
        />
        <TextField
          label={t("assistant_page.model")}
          value={values.model}
          onChange={(event) => setValues((v) => ({ ...v, model: event.target.value }))}
          required
          maxLength={200}
          autoComplete="off"
        />
        <TextField
          label={t("assistant_page.api_key")}
          type="password"
          hint={keyHint}
          value={values.api_key}
          onChange={(event) => setValues((v) => ({ ...v, api_key: event.target.value }))}
          required={!chat.api_key_set || chat.api_key_status === "needs_reentry"}
          maxLength={500}
          autoComplete="off"
        />
        <SelectField
          label={t("assistant_page.location")}
          value={values.locality}
          onChange={(locality) => setValues((v) => ({ ...v, locality: locality === "local" ? "local" : "cloud" }))}
          options={[
            { value: "cloud", label: t("assistant_page.cloud") },
            { value: "local", label: t("assistant_page.local") },
          ]}
        />
        {errors.form ? (
          <p role="alert" className="text-destructive">
            {errors.form}
          </p>
        ) : null}
        <div className="flex flex-wrap items-center gap-2">
          <Button type="submit">{t("assistant_page.save_endpoint")}</Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => void runTest()}
            disabled={testing || !settings.configured}
          >
            {t("assistant_page.test")}
          </Button>
          {chat.base_url ? (
            <Button type="button" variant="ghost" onClick={() => setRemoving(true)}>
              {t("assistant_page.remove")}
            </Button>
          ) : null}
          {saved ? <span role="status">{t("assistant_page.endpoint_saved")}</span> : null}
        </div>
      </form>
      {test ? (
        <ul aria-label={t("assistant_page.checks")} className="flex flex-col gap-1">
          {checks.map(([key, label]) => (
            <li key={key} className={cn(test.checks[key] ? "text-foreground" : "text-destructive")}>
              {t(`assistant_page.${label}`)}: {t(test.checks[key] ? "assistant_page.ok" : "assistant_page.failed")}
            </li>
          ))}
        </ul>
      ) : null}
      <Dialog open={removing} onOpenChange={setRemoving}>
        <DialogContent role="alertdialog" showCloseButton={false}>
          <DialogTitle>{t("assistant_page.remove_title")}</DialogTitle>
          <DialogDescription>{t("assistant_page.remove_body")}</DialogDescription>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoving(false)}>
              {t("assistant.cancel")}
            </Button>
            <Button variant="destructive" onClick={() => void remove()}>
              {t("assistant_page.remove_confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Section>
  );
}

// ---------------------------------------------------------------- M2S-E07-02
function Tools() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: tools = [] } = useQuery(assistantToolsListOptions());
  const [saved, setSaved] = useState(false);

  async function toggle(tool: ToolInfo) {
    setSaved(false);
    const off = tools.filter((x) => (x.name === tool.name ? x.enabled : !x.enabled)).map((x) => x.name);
    const { error } = await assistantSettingsUpdate({ body: { tools_disabled: off } });
    if (!error) {
      await queryClient.invalidateQueries({ queryKey: assistantToolsListQueryKey() });
      setSaved(true);
    }
  }

  function words(tool: ToolInfo): string {
    if (tool.annotations.read_only) return t("assistant_page.reads_only");
    if (tool.annotations.destructive) return t("assistant_page.deletes");
    return t("assistant_page.changes_data");
  }

  return (
    <Section label={t("assistant_page.tools")}>
      <ul aria-label={t("assistant_page.tools")} className="flex flex-col gap-2">
        {tools.map((tool) => (
          <li key={tool.name} className="flex items-start gap-3">
            <button
              type="button"
              role="switch"
              aria-checked={tool.enabled}
              aria-label={tool.name}
              onClick={() => void toggle(tool)}
              className={cn(
                "mt-1 h-5 w-9 shrink-0 rounded-full border-2 transition-colors",
                tool.enabled ? "border-primary bg-primary" : "border-input bg-muted",
              )}
            >
              <span
                className={cn(
                  "block h-4 w-4 rounded-full bg-background transition-transform",
                  tool.enabled ? "translate-x-4" : "translate-x-0",
                )}
              />
            </button>
            <div className="flex flex-col">
              <span className="font-mono text-sm">{tool.name}</span>
              <span className="text-sm text-muted-foreground">
                {tool.description} · {words(tool)}
              </span>
            </div>
          </li>
        ))}
      </ul>
      {saved ? <p role="status">{t("assistant_page.tools_saved")}</p> : null}
    </Section>
  );
}

// ---------------------------------------------------------------- M2S-E07-03
const PERIODS = { today: 1, last_7: 7, last_30: 30 } as const;

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function UsageSection({ settings }: { settings: Settings }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [period, setPeriod] = useState<keyof typeof PERIODS>("last_30");
  const from = isoDaysAgo(PERIODS[period] - 1);
  const query = (group_by: "day" | "user" | "model") => ({
    ...assistantUsageReadOptions({ query: { group_by, from } }),
    staleTime: 0,
  });
  const byDay = useQuery(query("day")).data;
  const byUser = useQuery(query("user")).data;
  const byModel = useQuery(query("model")).data;
  const [prices, setPrices] = useState({
    input: settings.prices.input_per_million?.toString() ?? "",
    output: settings.prices.output_per_million?.toString() ?? "",
  });
  const [pricesSaved, setPricesSaved] = useState(false);

  async function savePrices(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const num = (v: string) => (v.trim() === "" ? null : Number(v));
    const { error } = await assistantSettingsUpdate({
      body: { prices: { input_per_million: num(prices.input), output_per_million: num(prices.output) } },
    });
    if (!error) {
      setPricesSaved(true);
      await queryClient.invalidateQueries({
        predicate: (q) => (q.queryKey[0] as { _id?: string })?._id === "assistantUsageRead",
      });
    }
  }

  const cost = byDay?.totals.cost;
  return (
    <Section label={t("assistant_page.usage")}>
      <SelectField
        label={t("assistant_page.period")}
        value={period}
        onChange={(value) => setPeriod(value in PERIODS ? (value as keyof typeof PERIODS) : "last_30")}
        options={Object.keys(PERIODS).map((key) => ({ value: key, label: t(`assistant_page.${key}`) }))}
      />
      {cost ? <p>{t("assistant_page.cost", { amount: cost.amount.toFixed(2) })}</p> : null}
      <UsageTable label={t("assistant_page.by_day")} first={t("assistant_page.day")} groups={byDay?.groups} />
      <UsageTable label={t("assistant_page.by_member")} first={t("assistant_page.member")} groups={byUser?.groups} />
      <UsageTable
        label={t("assistant_page.by_model")}
        first={t("assistant_page.model_column")}
        groups={byModel?.groups}
      />
      <form onSubmit={savePrices} className="flex flex-col gap-3">
        <TextField
          label={t("assistant_page.price_input")}
          type="number"
          min={0}
          step="0.01"
          value={prices.input}
          onChange={(event) => setPrices((p) => ({ ...p, input: event.target.value }))}
        />
        <TextField
          label={t("assistant_page.price_output")}
          type="number"
          min={0}
          step="0.01"
          value={prices.output}
          onChange={(event) => setPrices((p) => ({ ...p, output: event.target.value }))}
        />
        <div className="flex items-center gap-2">
          <Button type="submit" variant="outline">
            {t("assistant_page.save_prices")}
          </Button>
          {pricesSaved ? <span role="status">{t("assistant_page.prices_saved")}</span> : null}
        </div>
      </form>
    </Section>
  );
}

function UsageTable({ label, first, groups }: { label: string; first: string; groups: UsageGroup[] | undefined }) {
  const { t } = useTranslation();
  const number = (n: number) => n.toLocaleString();
  return (
    <table aria-label={label} className="w-full text-left text-sm">
      <caption className="pb-1 text-left font-medium">{label}</caption>
      <thead>
        <tr className="border-b">
          <th scope="col" className="py-1">
            {first}
          </th>
          <th scope="col">{t("assistant_page.requests")}</th>
          <th scope="col">{t("assistant_page.input_tokens")}</th>
          <th scope="col">{t("assistant_page.output_tokens")}</th>
        </tr>
      </thead>
      <tbody>
        {(groups ?? []).length === 0 ? (
          <tr>
            <td colSpan={4} className="py-1 text-muted-foreground">
              {t("assistant_page.no_usage")}
            </td>
          </tr>
        ) : (
          (groups ?? []).map((g) => (
            <tr key={g.key} className="border-b">
              <th scope="row" className="py-1 font-normal">
                {g.label}
              </th>
              <td>
                {number(g.requests)}
                {g.unknown_requests ? ` (${number(g.unknown_requests)} ${t("assistant_page.unknown")})` : ""}
              </td>
              <td>{number(g.input_tokens)}</td>
              <td>{number(g.output_tokens)}</td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  );
}
