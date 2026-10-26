// SPDX-License-Identifier: MIT
// The tasks plugin's use of the assistant (M2S-E06-05, -06): availability and its two skills, through the
// generated client of @hauskraft/sdk-ts only.
import { assistantSkillsLatestOptions, assistantStatusOptions } from "@hauskraft/sdk-ts";
import { useQuery } from "@tanstack/react-query";

export const ADD_FROM_TEXT = "tasks.add-from-text";
export const WEEKLY_OVERVIEW = "tasks.weekly-overview";

/** True when an owner set up the assistant and this person may use it (403 counts as no). */
export function useAssistantAvailable(): boolean {
  const { data } = useQuery({ ...assistantStatusOptions(), retry: false, refetchInterval: 60_000 });
  return data?.available === true;
}

export function latestOverviewOptions() {
  return { ...assistantSkillsLatestOptions({ path: { skill_id: WEEKLY_OVERVIEW } }), retry: false };
}

export interface Suggestion {
  title: string;
  due_on: string | null;
}
