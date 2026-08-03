import type { CtaContent } from "@/lib/home";
import { resolveSiteCopyDeep } from "@/lib/site";
import type { Faq } from "@/lib/platform/faq";
import { answerEngineInsightsFaqDefaults } from "@shared/faq/defaults";
import { mergeFaqs, resolveFaqDefaults } from "@/lib/faqs";
import type { FaqDoc } from "@shared/faq";
import insightsVideoWebm from "@shared/assets/videos/website/answer-insight.webm";
import insightsVideoMp4 from "@shared/assets/videos/website/answer-insight.mp4";
import { appLinks } from "@/lib/app-links";
import type { HeroVideoSources } from "@/lib/platform/hero-video";

export const INSIGHTS_VIDEO: HeroVideoSources = {
  webm: insightsVideoWebm,
  mp4: insightsVideoMp4,
};

export type InsightsFeatureIcon =
  | "visibility"
  | "compare"
  | "platform"
  | "sentiment"
  | "citation";

export type InsightsFeature = {
  icon: InsightsFeatureIcon;
  title: string;
  bullets: string[];
  tags: string[];
  metric?: {
    label: string;
    delta: string;
    value: string;
  };
};

export const answerEngineInsightsFaqs: Faq[] = resolveFaqDefaults(
  answerEngineInsightsFaqDefaults,
);

export function mergeAnswerEngineInsightsFaqs(cms: FaqDoc[] | null | undefined): Faq[] {
  return mergeFaqs(cms, answerEngineInsightsFaqs);
}

export const answerEngineInsightsHero = {
  titleBefore: "了解 AI 如何回答关于",
  titleHighlight: "你品牌",
  titleAfter: "的问题",
  tagline: "看清你的品牌在 AI 回答中的真实位置，以及缺失的机会点",
  description:
    "监测您的品牌可见度、提及量和声量份额在人工智能生成的答案中的变化。让您了解自身所处的位置、与竞争对手的差距以及下一步的优化方向。",
  primaryCtaLabel: "获取演示",
  primaryCtaHref: appLinks.register,
  secondaryCtaLabel: "立即开始",
  secondaryCtaHref: appLinks.register,
};

export const answerEngineInsightsFeaturesHeader = {
  titleBefore: "全面的 AI 可见性与",
  titleHighlight: "竞争洞察",
  description: "从真实 AI 回答中，拆解可见度、竞争格局、情绪与信源结构。",
};

export const answerEngineInsightsFeatures: InsightsFeature[] = [
  {
    icon: "visibility",
    title: "多维可见度与行业位置",
    bullets: [
      "按时间、主题、平台追踪品牌与竞品在 AI 回答中的可见度变化。",
      "结合 Share of Voice 与行业排名，快速判断趋势走向与竞争格局变化。",
    ],
    tags: ["AI 可见度追踪", "竞品对标", "行业定位"],
    metric: { label: "可见性", delta: "+2.3%", value: "90.0" },
  },
  {
    icon: "compare",
    title: "真实问题下的竞争对比",
    bullets: [
      "基于真实用户提示词，展示品牌在单个问题中的提及情况、排序位置与竞品差距。",
      "识别尚未被现有内容充分覆盖或捕获的高价值搜索场景。",
    ],
    tags: ["提示词洞察", "机会缺口"],
  },
  {
    icon: "platform",
    title: "AI 平台偏好识别",
    bullets: [
      "对比品牌在不同 AI 平台的可见度、声量份额、排名与引用率表现。",
      "为 GEO 资源分配提供明确优先级依据。",
    ],
    tags: ["平台信号", "资源优先级", "GEO 策略"],
  },
  {
    icon: "sentiment",
    title: "AI 语境下的品牌情绪",
    bullets: [
      "监测 AI 对品牌的情绪分布及变化趋势。",
      "下钻到提示词层级，及时识别潜在风险与负面信号。",
    ],
    tags: ["风险信号", "品牌监控", "语境分析"],
  },
  {
    icon: "citation",
    title: "AI 信任来源解析",
    bullets: [
      "对引用来源的引文进行分类，以揭示 AI 引文偏好与 GEO 优化机会。",
      "结合行业领域，洞察 AI 的引用偏好，锁定差异化 GEO 优化机会。",
    ],
    tags: ["信任信号", "引用结构", "权威映射"],
  },
];

export const answerEngineInsightsCta: CtaContent = resolveSiteCopyDeep({
  badge: "准备就绪",
  titleBefore: "准备好查看你品牌的",
  titleHighlight: "信任分",
  titleAfter: "了吗？",
  description: "加入 {{siteName}}，共同追踪 AI 搜索可见度。基于数据洞察，告别盲目优化。",
  codeLines: ["// 停止猜测。", "// 开始掌控。"],
  secondaryCtaLabel: "联系我们",
  secondaryCtaHref: "/contact/",
  primaryCtaLabel: "注册试用",
  primaryCtaHref: appLinks.register,
});
