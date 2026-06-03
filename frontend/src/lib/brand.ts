import type { SamplingPlatform } from "@/types";

/** 试用套餐下最多可选平台数（与弹窗文案一致） */
export const PLATFORM_PLAN_LABEL = "Trial 7 Days";
export const PLATFORM_MAX_SELECTION = 1;
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
    return allPlatforms.filter((p) => saved.includes(p.platform));
  }
  return preferredDefaultSamplingPlatforms(allPlatforms);
}

export function platformAccent(provider: string): string {
  switch (provider) {
    case "doubao":
      return "bg-[#3370ff]/10 text-[#3370ff] border-[#3370ff]/20";
    case "deepseek":
      return "bg-[#4d6bfe]/10 text-[#4d6bfe] border-[#4d6bfe]/20";
    case "yuanbao":
      return "bg-[#12b76a]/10 text-[#12b76a] border-[#12b76a]/20";
    case "qianwen":
      return "bg-[#615fff]/10 text-[#615fff] border-[#615fff]/20";
    case "kimi":
      return "bg-foreground/5 text-foreground border-border";
    case "ernie":
      return "bg-[#2932e1]/10 text-[#2932e1] border-[#2932e1]/20";
    default:
      return "bg-muted text-foreground border-border";
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
