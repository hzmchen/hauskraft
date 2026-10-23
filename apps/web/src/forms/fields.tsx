// SPDX-License-Identifier: AGPL-3.0-or-later
// Labelled form fields for the M1* settings, setup and password pages: a visible label tied to the control, an
// optional hint (visible before typing) and an optional error next to the field, built only on @hauskraft/ui.
import { Input, cn } from "@hauskraft/ui";
import { useId, type ComponentProps } from "react";

function describedBy(...ids: (string | false | null | undefined)[]): string | undefined {
  return ids.filter(Boolean).join(" ") || undefined;
}

export function TextField({
  label,
  hint,
  error,
  className,
  ...input
}: { label: string; hint?: string; error?: string | null } & ComponentProps<typeof Input>) {
  const ids = { input: useId(), hint: useId(), error: useId() };
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <label htmlFor={ids.input} className="font-medium">
        {label}
      </label>
      <Input
        id={ids.input}
        aria-describedby={describedBy(hint && ids.hint, error && ids.error)}
        aria-invalid={error ? true : undefined}
        {...input}
      />
      {hint ? (
        <p id={ids.hint} className="text-sm text-muted-foreground">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={ids.error} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function SelectField({
  label,
  hint,
  value,
  onChange,
  options,
  className,
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
  options: readonly { value: string; label: string }[];
  className?: string;
}) {
  const ids = { select: useId(), hint: useId() };
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <label htmlFor={ids.select} className="font-medium">
        {label}
      </label>
      <select
        id={ids.select}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-describedby={hint ? ids.hint : undefined}
        className="h-control rounded-md border border-input bg-background px-2 text-foreground"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {hint ? (
        <p id={ids.hint} className="text-sm text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

/** The problem+json `code` of a failed generated-client call, if any. */
export function problemCode(error: unknown): string | undefined {
  return typeof error === "object" && error !== null && "code" in error ? String(error.code) : undefined;
}
