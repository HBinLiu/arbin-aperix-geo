/** 无 seed 时的默认头像底色（与早期单色头像一致） */
export const DEFAULT_USER_AVATAR_COLOR = "#3d7aed";

const AVATAR_SEED_KEY = "aperix_avatar_seed";

export function getStoredAvatarSeed(): string | null {
  try {
    return localStorage.getItem(AVATAR_SEED_KEY);
  } catch {
    return null;
  }
}

export function setStoredAvatarSeed(seed: string) {
  const normalized = seed.trim();
  if (!normalized) return;
  try {
    localStorage.setItem(AVATAR_SEED_KEY, normalized);
  } catch {
    /* ignore quota / private mode */
  }
}

export function clearStoredAvatarSeed() {
  try {
    localStorage.removeItem(AVATAR_SEED_KEY);
  } catch {
    /* ignore */
  }
}

/** 优先用当前 user.id，刷新首屏回退到本地缓存，避免默认色闪烁 */
export function resolveAvatarSeed(seed?: string): string | undefined {
  const trimmed = seed?.trim();
  if (trimmed) return trimmed;
  const stored = getStoredAvatarSeed()?.trim();
  return stored || undefined;
}

function hashString(input: string): number {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    hash = (hash * 31 + input.charCodeAt(i)) >>> 0;
  }
  return hash;
}

function hslToHex(hue: number, saturation: number, lightness: number): string {
  const h = hue / 360;
  const s = saturation / 100;
  const l = lightness / 100;
  const hue2rgb = (p: number, q: number, t: number) => {
    let tt = t;
    if (tt < 0) tt += 1;
    if (tt > 1) tt -= 1;
    if (tt < 1 / 6) return p + (q - p) * 6 * tt;
    if (tt < 1 / 2) return q;
    if (tt < 2 / 3) return p + (q - p) * (2 / 3 - tt) * 6;
    return p;
  };
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const r = Math.round(hue2rgb(p, q, h + 1 / 3) * 255);
  const g = Math.round(hue2rgb(p, q, h) * 255);
  const b = Math.round(hue2rgb(p, q, h - 1 / 3) * 255);
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}

/** 按用户标识生成稳定头像底色（饱和度/明度固定，保证白眼白嘴可读） */
export function userAvatarColor(seed: string): string {
  const normalized = seed.trim();
  if (!normalized) return DEFAULT_USER_AVATAR_COLOR;

  const hash = hashString(normalized);
  const hue = hash % 360;
  return hslToHex(hue, 65, 44);
}
