import type { SamplingPlatform } from "@/types";

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

/** 平台 logo 路径（对应 public/assets/imgs/）。 */
export function platformLogoSrc(provider: string): string | null {
  switch (provider) {
    case "deepseek":
      return "/assets/imgs/deepseek.png";
    case "doubao":
      return "/assets/imgs/doubao.png";
    case "yuanbao":
      return "/assets/imgs/yuanbao.png";
    case "kimi":
      return "/assets/imgs/kimi.png";
    case "ernie":
      return "/assets/imgs/ernie.png";
    case "qianwen":
      return "/assets/imgs/qianwen.png";
    default:
      return null;
  }
}
