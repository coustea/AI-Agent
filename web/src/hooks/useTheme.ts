import { useCallback, useEffect, useState } from "react";

export type ThemePreference = "system" | "light" | "dark";

const STORAGE_KEY = "color-scheme";

function readThemePreference(): ThemePreference {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === "light" || raw === "dark") return raw;
  } catch {
    // 忽略受限存储环境
  }
  return "system";
}

function applyThemePreference(pref: ThemePreference): void {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.classList.toggle("dark", pref === "dark" || (pref === "system" && prefersDark));
}

export function useTheme() {
  const [theme, setThemeState] = useState<ThemePreference>(readThemePreference);

  useEffect(() => {
    applyThemePreference(theme);
  }, [theme]);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const sync = () => {
      const current = readThemePreference();
      applyThemePreference(current);
      setThemeState(current);
    };
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY || e.key === null) sync();
    };
    mq.addEventListener("change", sync);
    window.addEventListener("storage", onStorage);
    return () => {
      mq.removeEventListener("change", sync);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const setTheme = useCallback((next: ThemePreference) => {
    try {
      if (next === "system") {
        localStorage.removeItem(STORAGE_KEY);
      } else {
        localStorage.setItem(STORAGE_KEY, next);
      }
    } catch {
      // 即使无法持久化也立即应用到当前页
    }
    setThemeState(next);
  }, []);

  return { theme, setTheme };
}
