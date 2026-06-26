import { useCallback, useState } from "react";

import { nextTheme, persistTheme, readStoredTheme, type ThemeMode } from "@/lib/theme";

export function useTheme() {
  const [theme, setThemeState] = useState<ThemeMode>(() => readStoredTheme());

  const setTheme = useCallback((mode: ThemeMode) => {
    persistTheme(mode);
    setThemeState(mode);
  }, []);

  const cycleTheme = useCallback(() => {
    setTheme(nextTheme(theme));
  }, [setTheme, theme]);

  return {
    theme,
    setTheme,
    cycleTheme,
    isDark: theme === "dark",
  };
}
