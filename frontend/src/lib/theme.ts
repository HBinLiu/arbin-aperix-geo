import { initDocumentIcons, LOGO_SRC } from "@/lib/assets/brand";

export type ThemeMode = "light" | "dark";

export const THEME_STORAGE_KEY = "aperix-theme";

export { LOGO_SRC };

/** 浅色主题用深色 logo，深色主题用浅色 logo（文件名指 logo 本身颜色）。 */
export function themeLogoSrc(mode: ThemeMode): string {
  return mode === "dark" ? LOGO_SRC.light : LOGO_SRC.dark;
}

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
  initDocumentIcons(themeLogoSrc(mode));
}

/** 挂载 React 前调用，避免首屏主题闪烁 */
export function initTheme(): void {
  const mode = readStoredTheme();
  applyTheme(mode);
  initDocumentIcons(themeLogoSrc(mode));
}

export function nextTheme(mode: ThemeMode): ThemeMode {
  return mode === "light" ? "dark" : "light";
}

export type ThemeTransitionOrigin = { x: number; y: number };

const THEME_TRANSITION_MS = 800;

function themeTransitionMaxRadius({ x, y }: ThemeTransitionOrigin): number {
  return Math.hypot(
    Math.max(x, window.innerWidth - x),
    Math.max(y, window.innerHeight - y),
  );
}

function prefersReducedThemeMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** 从点击位置圆形扩散切换主题；不支持时回退为即时切换 */
export function persistThemeWithTransition(
  mode: ThemeMode,
  origin?: ThemeTransitionOrigin,
  onApplied?: () => void,
): void {
  const apply = () => {
    persistTheme(mode);
    onApplied?.();
  };

  if (
    !origin ||
    prefersReducedThemeMotion() ||
    typeof document.startViewTransition !== "function"
  ) {
    apply();
    return;
  }

  const transition = document.startViewTransition(apply);

  void transition.ready.then(() => {
    const radius = themeTransitionMaxRadius(origin);
    document.documentElement.animate(
      {
        clipPath: [
          `circle(0px at ${origin.x}px ${origin.y}px)`,
          `circle(${radius}px at ${origin.x}px ${origin.y}px)`,
        ],
      },
      {
        duration: THEME_TRANSITION_MS,
        easing: "ease-in-out",
        pseudoElement: "::view-transition-new(root)",
      },
    );
  });
}
