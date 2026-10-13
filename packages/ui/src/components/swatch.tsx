// SPDX-License-Identifier: MIT
// A colour chip for theme previews (M0S-E13-07). The colour is data from a theme's preview, not a style
// choice, so it travels as a CSS variable and is painted by the bg-swatch utility.
import type { CSSProperties } from "react";

import { cn } from "../lib/utils";

export function Swatch({ color, className }: { color: string; className?: string }) {
  return (
    <span
      aria-hidden="true"
      data-slot="swatch"
      className={cn("inline-block size-5 rounded-sm border bg-swatch", className)}
      style={{ "--swatch": color } as CSSProperties}
    />
  );
}
