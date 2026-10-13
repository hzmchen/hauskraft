// SPDX-License-Identifier: MIT
// <Icon name="…"> (spec §10.2.6, M0S-E13-02): the active theme's sprite if it lists the name, otherwise
// the default pack. Decorative (aria-hidden) unless it has a label.
import { createContext, useContext, useMemo, type ReactNode } from "react";

import { cn } from "../lib/utils";
import type { IconName } from "../theme/contract.gen";
import { DEFAULT_PACK, UNKNOWN_ICON } from "./default-pack";

interface IconSource {
  spriteUrl: string | null;
  names: ReadonlySet<string>;
}

const IconContext = createContext<IconSource>({ spriteUrl: null, names: new Set() });

/** The shell wraps the app with the active theme's `icons` (from GET /api/v1/theme). */
export function IconProvider({
  spriteUrl,
  names,
  children,
}: {
  spriteUrl: string | null;
  names: readonly string[];
  children: ReactNode;
}) {
  const value = useMemo(() => ({ spriteUrl, names: new Set(names) }), [spriteUrl, names]);
  return <IconContext.Provider value={value}>{children}</IconContext.Provider>;
}

export interface IconProps {
  name: IconName | (string & {});
  /** Accessible name; without it the icon is hidden from assistive technology. */
  label?: string;
  className?: string;
}

export function Icon({ name, label, className }: IconProps) {
  const { spriteUrl, names } = useContext(IconContext);
  const a11y = label ? { role: "img", "aria-label": label } : { "aria-hidden": true as const };
  const classes = cn("size-4 shrink-0", className);
  if (spriteUrl && names.has(name)) {
    return (
      <svg {...a11y} data-icon={name} className={classes} viewBox="0 0 24 24" fill="currentColor">
        <use href={`${spriteUrl}#${name}`} />
      </svg>
    );
  }
  const Glyph = DEFAULT_PACK[name as IconName] ?? UNKNOWN_ICON;
  return <Glyph {...a11y} data-icon={name} className={classes} />;
}
