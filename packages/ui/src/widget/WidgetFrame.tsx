// SPDX-License-Identifier: MIT
// The frame every dashboard widget renders in (M0S-E13-02). The theme decides the chrome
// (data-hauskraft-chrome) and the title bar (data-hauskraft-header); the region, heading level and
// accessible name are the same in every variant.
import { useId, type ReactNode } from "react";

import { cn } from "../lib/utils";

export interface WidgetFrameProps {
  /** Shown as the heading and used as the region's accessible name. */
  title: string;
  /** Buttons or links in the title bar. */
  actions?: ReactNode;
  /** Heading level inside the page; 2 on the dashboard. */
  headingLevel?: 2 | 3;
  className?: string;
  children?: ReactNode;
}

export function WidgetFrame({ title, actions, headingLevel = 2, className, children }: WidgetFrameProps) {
  const headingId = useId();
  const Heading = headingLevel === 2 ? "h2" : "h3";
  return (
    <section
      aria-labelledby={headingId}
      data-slot="widget"
      className={cn(
        "flex h-full flex-col overflow-hidden rounded-lg border border-widget-border bg-widget text-widget-foreground",
        "chrome-flat:border-0 chrome-flat:bg-transparent chrome-flat:text-foreground",
        "chrome-elevated:border-0 chrome-elevated:shadow-md",
        "chrome-tinted:border-0 chrome-tinted:bg-secondary chrome-tinted:text-secondary-foreground",
        className,
      )}
    >
      <header
        data-slot="widget-header"
        className="flex items-center justify-between gap-density px-density pt-3 header-banner:bg-primary header-banner:pb-2 header-banner:pt-2 header-banner:text-primary-foreground"
      >
        <Heading id={headingId} className="font-heading text-lg font-bold">
          {title}
        </Heading>
        {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
      </header>
      <div data-slot="widget-body" className="min-h-0 flex-1 overflow-auto p-density">
        {children}
      </div>
    </section>
  );
}
