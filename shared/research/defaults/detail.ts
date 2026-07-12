import type { ResearchHeroDetail, ResearchSidebarCta } from "../types";

export const researchSidebarDefault: ResearchSidebarCta = {
  kicker: "{{siteName}} 诊断",
  title: "你的品牌正在被 AI 选择吗？",
  description:
    "在 AI 答案引擎中将你的品牌与竞争对手对标，然后把可见性差距转化为内容、引用、发布和证据网络动作。",
  bullets: [
    "追踪 ChatGPT、Perplexity、Gemini、Google AI Mode、Grok、Copilot 和 Google Overview",
    "识别被引用来源、扇出缺口和覆盖不足的行业主题",
    "从监测推进到 GEO 执行、第三方证据和推荐提升",
  ],
  primaryLabel: "生成免费诊断",
  primaryHref: "/auth/register",
  secondaryLabel: "安排演示",
  secondaryHref: "/contact/",
  footnote: "为营销、SEO、GEO 和品牌团队打造。无需安装。",
};

export function buildResearchHeroFallback(
  _slug: string,
  cardTitle: string,
  cardDescription: string,
): ResearchHeroDetail {
  return {
    badge: "行业研究报告",
    titleBefore: cardTitle,
    titleAccent: "",
    titleAfter: "",
    subtitle: cardDescription,
    metaLinks: [
      { label: "开始免费试用", href: "/auth/register" },
      { label: "预约演示", href: "/contact/" },
    ],
    metaStats: [],
    actions: [
      { label: "获取完整报告", href: "/contact/" },
      { label: "了解 {{siteName}}", href: "/" },
    ],
    proof: ["无需信用卡", "为 SEO、GEO 和品牌团队打造"],
  };
}
