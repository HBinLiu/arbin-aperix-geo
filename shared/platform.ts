/** 采样平台元数据与 logo 路径（frontend / website 共用） */

export type PlatformId = "doubao" | "deepseek" | "qianwen" | "yuanbao" | "ernie" | "kimi";

export type PlatformInfo = {
  id: PlatformId;
  label: string;
  logoFile: string;
};

export const PLATFORMS: PlatformInfo[] = [
  { id: "doubao", label: "豆包", logoFile: "doubao.png" },
  { id: "deepseek", label: "DeepSeek", logoFile: "deepseek.png" },
  { id: "qianwen", label: "千问", logoFile: "qianwen.png" },
  { id: "yuanbao", label: "元宝", logoFile: "yuanbao.png" },
  { id: "kimi", label: "Kimi", logoFile: "kimi.png" },
  { id: "ernie", label: "文心一言", logoFile: "ernie.png" },
];

export const PLATFORM_BY_ID = Object.fromEntries(PLATFORMS.map((p) => [p.id, p])) as Record<
  PlatformId,
  PlatformInfo
>;

/** 官网 Hero 等平台展示顺序 */
export const HERO_PLATFORM_IDS: PlatformId[] = PLATFORMS.map((p) => p.id);

const PLATFORM_ALIASES: Record<string, PlatformId> = {
  豆包: "doubao",
  deepseek: "deepseek",
  千问: "qianwen",
  通义千问: "qianwen",
  qwen: "qianwen",
  元宝: "yuanbao",
  腾讯元宝: "yuanbao",
  kimi: "kimi",
  文心一言: "ernie",
  文心: "ernie",
};

export function isPlatformId(value: string): value is PlatformId {
  return value in PLATFORM_BY_ID;
}

export function resolvePlatformId(value: string): PlatformId | null {
  const trimmed = value.trim();
  if (isPlatformId(trimmed)) return trimmed;
  const alias = PLATFORM_ALIASES[trimmed] ?? PLATFORM_ALIASES[trimmed.toLowerCase()];
  if (alias) return alias;
  const byLabel = PLATFORMS.find((p) => p.label.toLowerCase() === trimmed.toLowerCase());
  return byLabel?.id ?? null;
}

export function resolvePlatformIds(values: string[]): PlatformId[] {
  const seen = new Set<PlatformId>();
  const out: PlatformId[] = [];
  for (const value of values) {
    const id = resolvePlatformId(value);
    if (id && !seen.has(id)) {
      seen.add(id);
      out.push(id);
    }
  }
  return out;
}

/** 静态站点 / 控制台 public 目录下的 URL */
export function platformLogoPublicPath(id: PlatformId): string {
  return `/assets/platform/${PLATFORM_BY_ID[id].logoFile}`;
}

export function platformLabel(id: PlatformId): string {
  return PLATFORM_BY_ID[id].label;
}
