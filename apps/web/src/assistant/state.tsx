// SPDX-License-Identifier: AGPL-3.0-or-later
// The assistant's availability and the side panel's open state (M2S-E06-01). Open or closed is remembered per
// device; storage can be blocked, so it falls back to closed.
import { assistantStatusOptions } from "@hauskraft/sdk-ts";
import { useQuery } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";

import { can, useSession } from "../session";

const KEY = "hauskraft.assistant.open";

function stored(): boolean {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

interface PanelState {
  open: boolean;
  setOpen: (open: boolean) => void;
  buttonRef: RefObject<HTMLButtonElement | null>;
  /** The shell header: on narrow screens the panel covers the page below it, so the header stays usable. */
  headerRef: RefObject<HTMLElement | null>;
}

const PanelContext = createContext<PanelState | null>(null);

export function AssistantProvider({ children }: { children: ReactNode }) {
  const [open, setOpenState] = useState(stored);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const headerRef = useRef<HTMLElement>(null);
  const setOpen = useCallback((next: boolean) => {
    setOpenState(next);
    try {
      localStorage.setItem(KEY, next ? "1" : "0");
    } catch {
      // storage blocked: the panel just doesn't remember
    }
  }, []);
  const value = useMemo(() => ({ open, setOpen, buttonRef, headerRef }), [open, setOpen]);
  return <PanelContext.Provider value={value}>{children}</PanelContext.Provider>;
}

export function usePanel(): PanelState {
  const state = useContext(PanelContext);
  if (!state) throw new Error("usePanel needs <AssistantProvider>");
  return state;
}

/** True when the person may use the assistant and an owner has set it up. */
export function useAssistantAvailable(): boolean {
  const session = useSession();
  const allowed = can(session, "assistant.use");
  const { data } = useQuery({ ...assistantStatusOptions(), enabled: allowed, refetchInterval: 60_000 });
  return allowed && data?.available === true;
}

/** The bottom edge of an element in the viewport, kept current while it resizes. */
export function useBottomEdge(ref: RefObject<HTMLElement | null>): number {
  const [bottom, setBottom] = useState(0);
  useEffect(() => {
    const element = ref.current;
    if (!element) return undefined;
    const measure = () => setBottom(element.getBoundingClientRect().bottom);
    measure();
    if (typeof ResizeObserver !== "function") return undefined;
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref]);
  return bottom;
}
