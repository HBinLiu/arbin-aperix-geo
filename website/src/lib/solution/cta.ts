import type { CtaContent } from "@/lib/home";
import { resolveSiteCopyDeep } from "@/lib/site";

export function createSolutionCta(description: string): CtaContent {
  return resolveSiteCopyDeep({
    badge: "准备就绪",
    titleBefore: "可能相关的",
    titleHighlight: "问题",
    titleAfter: "",
    description,
    codeLines: ["// 停止猜测。", "// 开始掌控。"],
    secondaryCtaLabel: "获取演示",
    secondaryCtaHref: "/auth/register",
    primaryCtaLabel: "开始免费试用",
    primaryCtaHref: "/auth/register",
  });
}
