import { useCallback, useState } from "react";

import { nextTheme, persistThemeWithTransition, readStoredTheme, type ThemeMode, type ThemeTransitionOrigin } from "@/lib/theme";

export type { ThemeTransitionOrigin };

export function useTheme() {
  const [theme, setThemeState] = useState<ThemeMode>(() => readStoredTheme());

  const setTheme = useCallback((mode: ThemeMode, origin?: ThemeTransitionOrigin) => {
    persistThemeWithTransition(mode, origin, () => setThemeState(mode));
  }, []);

  const cycleTheme = useCallback(
    (origin?: ThemeTransitionOrigin) => {
      const next = nextTheme(theme);
      persistThemeWithTransition(next, origin, () => setThemeState(next));
    },
    [theme],
  );

  return {
    theme,
    setTheme,
    cycleTheme,
    isDark: theme === "dark",
  };
}
