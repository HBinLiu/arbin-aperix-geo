import type { CtaContent } from "@/lib/home";
import type { PlatformFaqItem } from "@/lib/platform/faq";
import type { PageSeo } from "@/lib/seo";

export const CONTENT_CREATION_OPTIMIZATION_PATH = "/platform/content-creation-optimization";

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

export type ContentCreationFaqItem = PlatformFaqItem;

export const contentCreationSeo: PageSeo = {
  title: "AI 智能内容优化引擎 | Aperix AI",
  description:
    "创作针对搜索引擎和 AI 平台优化的高质量文章。内置 SEO/GEO 优化的内容简报、大纲和完整文章。",
};

export const contentCreationHero = {
  titleBefore: "创作既能",
  titleHighlight: "排名",
  titleAfter: "又能被引用的内容",
  tagline: "从选题到发布 —— AI 指导每一步。从第一天起就为 Google 排名和 AI 引用而生。",
  description:
    "创作针对搜索引擎和 AI 平台优化的高质量文章。内置 SEO/GEO 优化的内容简报、大纲和完整文章。",
  primaryCtaLabel: "开始创作",
  primaryCtaHref: "/auth/register",
  secondaryCtaLabel: "获取演示",
  secondaryCtaHref: "/auth/register",
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

export const contentCreationBenefits = {
  title: "为什么选择 Aperix AI 进行创作？",
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
};

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

export const contentCreationFaqs: ContentCreationFaqItem[] = [
  {
    number: "01",
    label: "定位",
    question: "Aperix AI 内容创作和传统 AI 写作工具有什么不同？",
    paragraphs: [
      "传统 AI 写作工具关注「写得快」，而 Aperix AI 关注「写得能被找到、被引用」。",
      "平台从选题阶段就结合 SEO 与 GEO 信号，确保内容同时面向搜索排名与 AI 回答场景进行结构设计。",
    ],
  },
  {
    number: "02",
    label: "流程",
    question: "从选题到发布，Aperix AI 如何指导每一步？",
    paragraphs: ["完整工作流覆盖四个阶段："],
    bullets: [
      "发现：基于 SEO + GEO 数据识别高潜力话题",
      "大纲：生成结构化、易引用的内容框架",
      "创作：在实时优化建议下完成撰写",
      "发布：导出至 WordPress、Notion 等 CMS",
    ],
    closingParagraphs: ["让团队不再在多个工具之间切换，而是在同一流程中完成策略与执行。"],
  },
  {
    number: "03",
    label: "优化",
    question: "内容如何同时兼顾 Google 排名和 AI 引用？",
    paragraphs: [
      "Aperix AI 会从关键词覆盖、实体识别、话题深度、语义结构、易引用格式与可读性等维度进行优化。",
      "写作过程中持续给出评分与修复建议，例如补充 FAQ、添加数据点、优化章节层级等，帮助内容在发布前达到 SEO 与 GEO 双重标准。",
    ],
  },
  {
    number: "04",
    label: "语言",
    question: "是否支持多语言内容创作？",
    paragraphs: [
      "支持。Aperix AI 覆盖 20 多种语言的内容创作与优化，帮助团队在不同市场以母语级质量产出内容。",
      "同一套 SEO/GEO 优化逻辑可应用于多语言场景，确保全球内容策略保持一致。",
    ],
  },
];

export const contentCreationCta: CtaContent = {
  badge: "准备就绪",
  titleBefore: "准备好创作",
  titleHighlight: "高质量",
  titleAfter: "的内容了吗？",
  description: "从免费的话题分析开始，看看您能占据哪些排名。",
  codeLines: ["// 停止猜测。", "// 开始掌控。"],
  secondaryCtaLabel: "获取演示",
  secondaryCtaHref: "/auth/register",
  primaryCtaLabel: "开始免费试用",
  primaryCtaHref: "/auth/register",
};
