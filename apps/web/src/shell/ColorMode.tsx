// SPDX-License-Identifier: AGPL-3.0-or-later
// Colour mode per device (M0S-E08-02): system (default), light or dark. Stored only in this browser
// (localStorage "hauskraft.mode"), never sent to the server, and independent of the household theme.
// index.html applies the same rule before first paint; this provider keeps it in sync afterwards.
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";

export const MODES = ["system", "light", "dark"] as const;
export type ColorMode = (typeof MODES)[number];
export const MODE_STORAGE_KEY = "hauskraft.mode";
const DARK_QUERY = "(prefers-color-scheme: dark)";

function readMode(): ColorMode {
  try {
    const value = localStorage.getItem(MODE_STORAGE_KEY);
    return (MODES as readonly string[]).includes(value ?? "") ? (value as ColorMode) : "system";
  } catch {
    return "system"; // storage blocked: fall back to system
  }
}

function writeMode(mode: ColorMode): void {
  try {
    localStorage.setItem(MODE_STORAGE_KEY, mode);
  } catch {
    // storage blocked: the choice holds for this session only
  }
}

function systemIsDark(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(DARK_QUERY).matches;
}

/** Follow the OS setting live (prefers-color-scheme). */
function subscribeToSystem(onChange: () => void): () => void {
  if (typeof window.matchMedia !== "function") return () => undefined;
  const query = window.matchMedia(DARK_QUERY);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

interface ColorModeValue {
  mode: ColorMode;
  isDark: boolean;
  setMode: (mode: ColorMode) => void;
}

const ColorModeContext = createContext<ColorModeValue | null>(null);

export function ColorModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ColorMode>(readMode);
  const systemDark = useSyncExternalStore(subscribeToSystem, systemIsDark, () => false);

  const isDark = mode === "dark" || (mode === "system" && systemDark);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
  }, [isDark]);

  const setMode = useCallback((next: ColorMode) => {
    writeMode(next);
    setModeState(next);
  }, []);

  const value = useMemo(() => ({ mode, isDark, setMode }), [mode, isDark, setMode]);
  return <ColorModeContext.Provider value={value}>{children}</ColorModeContext.Provider>;
}

export function useColorMode(): ColorModeValue {
  const value = useContext(ColorModeContext);
  if (!value) throw new Error("useColorMode needs a ColorModeProvider");
  return value;
}

/** The "Colour mode" radio group (System, Light, Dark), used in Settings → Appearance. */
export function ColorModeControl() {
  const { t } = useTranslation();
  const { mode, setMode } = useColorMode();
  const labelId = useId();
  const name = useId();
  return (
    <div role="radiogroup" aria-labelledby={labelId} className="flex flex-col gap-2">
      <span id={labelId} className="font-medium">
        {t("mode.label")}
      </span>
      <div className="flex flex-wrap gap-4">
        {MODES.map((option) => (
          <label key={option} className="flex items-center gap-2">
            <input
              type="radio"
              name={name}
              value={option}
              checked={mode === option}
              onChange={() => setMode(option)}
              className="size-4 accent-primary"
            />
            {t(`mode.${option}`)}
          </label>
        ))}
      </div>
    </div>
  );
}
