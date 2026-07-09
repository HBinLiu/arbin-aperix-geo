import type { SamplingPlatform } from "@/types";
import { PLATFORM_LOGO_SRC } from "@/lib/assets/platform";
import { isPlatformId } from "@shared/platform";

export const DEFAULT_SAMPLING_PROVIDER = "doubao";

export function preferredDefaultSamplingPlatforms(platforms: SamplingPlatform[]): SamplingPlatform[] {
  if (platforms.length === 0) return [];
  const preferred = platforms.find((p) => p.platform === DEFAULT_SAMPLING_PROVIDER);
  const fallback = preferred ?? platforms[0];
  return [fallback];
}

/** 主体已保存的平台；未配置时回退默认平台。 */
export function effectiveSamplingPlatforms(
  subject: { sampling_platforms?: string[] },
  allPlatforms: SamplingPlatform[],
): SamplingPlatform[] {
  const saved = subject.sampling_platforms ?? [];
  if (saved.length > 0) {
    const byId = Object.fromEntries(allPlatforms.map((p) => [p.platform, p]));
    return saved.map((id) => byId[id]).filter((p): p is SamplingPlatform => p != null);
  }
  return preferredDefaultSamplingPlatforms(allPlatforms);
}

export function platformAccent(provider: string): string {
  switch (provider) {
    case "doubao":
      return "bg-doubao/10 text-doubao border-doubao/20";
    case "deepseek":
      return "bg-deepseek/10 text-deepseek border-deepseek/20";
    case "yuanbao":
      return "bg-yuanbao/10 text-yuanbao border-yuanbao/20";
    case "qianwen":
      return "bg-qianwen/10 text-qianwen border-qianwen/20";
    case "kimi":
      return "bg-kimi/10 text-kimi border-kimi/20";
    case "ernie":
      return "bg-ernie/10 text-ernie border-ernie/20";
    default:
      return "bg-background text-foreground border-border";
  }
}

/** 平台 logo（Vite 打包 URL） */
export function platformLogoSrc(provider: string): string | null {
  if (!isPlatformId(provider)) return null;
  return PLATFORM_LOGO_SRC[provider];
}
