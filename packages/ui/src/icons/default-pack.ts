// SPDX-License-Identifier: MIT
// The default icon pack: Lucide (ISC) for every core name (spec §10.2.6). Themes may override any
// subset with their sprite; plugins add names with their own default SVGs.
import {
  Activity,
  AlarmClock,
  CalendarDays,
  Check,
  CircleCheck,
  CircleDashed,
  CircleUser,
  Clock,
  ListChecks,
  Monitor,
  Moon,
  Pencil,
  Plus,
  Settings,
  Sun,
  Trash2,
  TriangleAlert,
  X,
  type LucideIcon,
} from "lucide-react";

import type { IconName } from "../theme/contract.gen";

export const DEFAULT_PACK: Record<IconName, LucideIcon> = {
  "nav.today": CalendarDays,
  "nav.tasks": ListChecks,
  "nav.activity": Activity,
  "nav.settings": Settings,
  "action.add": Plus,
  "action.edit": Pencil,
  "action.delete": Trash2,
  "action.confirm": Check,
  "action.cancel": X,
  "status.done": CircleCheck,
  "status.due": Clock,
  "status.overdue": AlarmClock,
  "user.menu": CircleUser,
  "mode.system": Monitor,
  "mode.light": Sun,
  "mode.dark": Moon,
  "widget.unavailable": TriangleAlert,
};

/** Shown for a name nobody provides, so a missing icon never breaks a view. */
export const UNKNOWN_ICON: LucideIcon = CircleDashed;
