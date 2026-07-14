import type { CtaContent } from "@/lib/home";
import { resolveSiteCopyDeep } from "@/lib/site";
import type { Faq } from "@/lib/platform/faq";
import { contentCreationFaqDefaults } from "@shared/faq/defaults";
import { mergeFaqs, resolveFaqDefaults } from "@/lib/faqs";
import type { FaqDoc } from "@shared/faq";
import { appLinks } from "@/lib/app-links";

export type ContentCreationFeatureIcon = "topic" | "outline" | "draft" | "quality";

export type ContentCreationFeature = {
  icon: ContentCreationFeatureIcon;
  title: string;
  description: string;
  tag: string;
};

export type ContentCreationWorkflowIcon = "discover" | "outline" | "draft" | "publish";

export type ContentCreationWorkflowStep = {
  step: string;
  title: string;
  description: string;
  icon: ContentCreationWorkflowIcon;
};

export type ContentCreationBenefit = {
  number: string;
  title: string;
  description: string;
};

export const contentCreationFaqs: Faq[] = resolveFaqDefaults(contentCreationFaqDefaults);

export function mergeContentCreationFaqs(cms: FaqDoc[] | null | undefined): Faq[] {
  return mergeFaqs(cms, contentCreationFaqs);
}

export const contentCreationHero = {
  titleBefore: "创作既能",
  titleHighlight: "排名",
  titleAfter: "又能被引用的内容",
  tagline: "从选题到发布 —— AI 指导每一步。从第一天起就为 Google 排名和 AI 引用而生。",
  description:
    "创作针对搜索引擎和 AI 平台创作的高质量文章。内置 SEO/GEO 优化的内容简报、大纲和完整文章。",
  primaryCtaLabel: "开始创作",
  primaryCtaHref: appLinks.register,
  secondaryCtaLabel: "获取演示",
  secondaryCtaHref: appLinks.register,
};

export const contentCreationRankingFactors = [
  "关键词优化",
  "实体覆盖",
  "话题深度",
  "语义结构",
  "易引用格式",
  "可读性平衡",
] as const;

export const contentCreationRankingNote = "每一篇内容都针对 6 个以上的影响因子进行了优化";

export const contentCreationWorkflow = {
  title: "从创意到发布 —— 仅需几分钟",
  steps: [
    {
      step: "步骤 1",
      title: "发现",
      description: "利用 SEO + GEO 数据寻找高潜力话题",
      icon: "discover",
    },
    {
      step: "步骤 2",
      title: "大纲",
      description: "AI 生成结构化、易于被引用的内容大纲",
      icon: "outline",
    },
    {
      step: "步骤 3",
      title: "创作",
      description: "在实时优化指导下进行撰写",
      icon: "draft",
    },
    {
      step: "步骤 4",
      title: "发布",
      description: "导出至 WordPress、Notion 或任何 CMS",
      icon: "publish",
    },
  ] satisfies ContentCreationWorkflowStep[],
};

export const contentCreationFeaturesHeader = {
  titleBefore: "为",
  titleHighlight: "AI 搜索时代",
  titleAfter: "而生",
  description: "不只是又一个 AI 写作工具。专为产出高效能内容而设计。",
};

export const contentCreationFeatures: ContentCreationFeature[] = [
  {
    icon: "topic",
    title: "话题研究",
    description: "寻找那些您可以同时赢得 Google 和 AI 认可的话题",
    tag: "结合 GEO + SEO 信号",
  },
  {
    icon: "outline",
    title: "智能大纲",
    description: "AI 构建既能排名又能被引用的内容结构",
    tag: "标题建议 + FAQ 板块",
  },
  {
    icon: "draft",
    title: "AI 起草助手",
    description: "在上下文语境下协助完成各章节撰写",
    tag: "保持您的品牌调性",
  },
  {
    icon: "quality",
    title: "质量评分",
    description: "关于可读性和引用潜力的实时反馈",
    tag: "发布前确保评分达 80+",
  },
];

export const contentCreationBenefits = resolveSiteCopyDeep({
  title: "为什么选择 {{siteName}} 进行创作？",
  items: [
    {
      number: "1",
      title: "双重优化",
      description: "每一篇内容都针对 Google 和 AI 引用同步优化",
    },
    {
      number: "2",
      title: "数据驱动选题",
      description: "仅创作那些已被证明具有搜索和 AI 需求的内容",
    },
    {
      number: "3",
      title: "易引用结构",
      description: "格式化处理，让 AI 模型能轻松引用您的内容",
    },
  ] satisfies ContentCreationBenefit[],
});

export const contentCreationLocales = {
  title: "多语言支持",
  languages: ["English", "中文", "Español", "Français", "Deutsch", "日本語", "以及更多"],
  description: "支持 20 多种语言的内容创作与优化，产出母语级质量的内容。",
};

export const contentCreationIntegrations = {
  title: "全平台发布",
  platforms: ["WordPress", "Notion", "Halo", "HubSpot", "Ghost", "Webflow", "Markdown"],
  badge: "发布就绪",
};

export const contentCreationCta: CtaContent = {
  badge: "准备就绪",
  titleBefore: "准备好创作",
  titleHighlight: "高质量",
  titleAfter: "的内容了吗？",
  description: "从免费的话题分析开始，看看您能占据哪些排名。",
  codeLines: ["// 停止猜测。", "// 开始掌控。"],
  secondaryCtaLabel: "获取演示",
  secondaryCtaHref: appLinks.register,
  primaryCtaLabel: "开始免费试用",
  primaryCtaHref: appLinks.register,
};
