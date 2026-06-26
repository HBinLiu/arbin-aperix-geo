export type ThemeMode = "light" | "dark";

export const THEME_STORAGE_KEY = "aperix-theme";

function getSystemTheme(): ThemeMode {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function readStoredTheme(): ThemeMode {
  if (typeof window === "undefined") return "light";
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
    if (stored === "system") {
      const migrated = getSystemTheme();
      localStorage.setItem(THEME_STORAGE_KEY, migrated);
      return migrated;
    }
  } catch {
    /* localStorage 不可用时默认浅色 */
  }
  return "light";
}

export function applyTheme(mode: ThemeMode): void {
  if (typeof document === "undefined") return;
  document.documentElement.classList.toggle("dark", mode === "dark");
}

export function persistTheme(mode: ThemeMode): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, mode);
  } catch {
    /* 忽略写入失败 */
  }
  applyTheme(mode);
}

/** 挂载 React 前调用，避免首屏主题闪烁 */
export function initTheme(): void {
  applyTheme(readStoredTheme());
}

export function nextTheme(mode: ThemeMode): ThemeMode {
  return mode === "light" ? "dark" : "light";
}
