import type { CtaContent } from "@/lib/home";
import { resolveSiteCopyDeep } from "@/lib/site";
import type { PlatformFaqItem } from "@/lib/platform/faq";
import promptExplorerVideo from "@shared/assets/videos/website/prompt-explorer.webm";

export const PROMPT_VIDEO_URL = promptExplorerVideo;

export type PromptFeatureIcon = "intent" | "funnel" | "fanout" | "platform-diff" | "trend";

export type PromptFeature = {
  icon: PromptFeatureIcon;
  title: string;
  bullets: string[];
  tags: string[];
  metric?: {
    label: string;
    delta: string;
    value: string;
  };
};

export type PromptFaqItem = PlatformFaqItem;

export const promptExplorerHero = {
  titleBefore: "了解",
  titleHighlight: "AI问题",
  titleAfter: "背后的需求结构",
  tagline: "看清用户需求如何被 AI 理解、拆解并排序",
  description:
    "通过分析真实提示词与查询扇出，帮助您看清用户需求是如何被理解、被拆分并被逐层放大的，从而判断哪些问题值得投入，哪些只是表层噪音。",
  primaryCtaLabel: "获取演示",
  primaryCtaHref: "/auth/register",
  secondaryCtaLabel: "立即开始",
  secondaryCtaHref: "/auth/register",
};

export const promptExplorerFeaturesHeader = {
  titleBefore: "解构真实问题，",
  titleHighlight: "理解需求如何形成",
  description: "通过提示词、决策阶段与查询扇出，理解需求的深度与价值。",
};

export const promptExplorerFeatures: PromptFeature[] = [
  {
    icon: "intent",
    title: "从提示词层级洞察真实用户意图",
    bullets: [
      "分析品牌在真实提示词中的呈现方式，包括可见度、排名与情绪反馈。",
      "帮助你理解用户真正关心的问题，而不只是关键词层面的假设。",
    ],
    tags: ["用户意图", "提示词分析", "品牌可见度"],
  },
  {
    icon: "funnel",
    title: "识别问题所处的决策阶段",
    bullets: [
      "将提示词按 TOFU、MOFU、BOFU 阶段分类，区分认知、比较与决策。",
      "聚焦更接近转化的问题，或更适合用于长期认知建设的内容方向。",
    ],
    tags: ["需求漏斗", "决策阶段"],
  },
  {
    icon: "fanout",
    title: "查询扇出深度分析",
    bullets: [
      "观察 AI 如何将一个问题扩展为多个子问题和探索路径。",
      "分值越高，代表需求越复杂，也往往意味着更高的内容与产品布局价值。",
    ],
    tags: ["查询扇出", "提示词工程"],
  },
  {
    icon: "platform-diff",
    title: "不同 AI 平台的答案结构差异",
    bullets: [
      "对比豆包、DeepSeek、千问等平台对同一问题的拆解方式与侧重点。",
      "判断在哪些平台需要更系统化的内容结构，而非简单复用通用答案。",
    ],
    tags: ["平台差异", "内容结构"],
  },
  {
    icon: "trend",
    title: "趋势变化中的需求信号",
    bullets: [
      "追踪查询量与趋势变化，识别正在增长、趋于稳定或逐步衰退的问题。",
      "为内容与产品投入提供时间维度上的决策依据。",
    ],
    tags: ["趋势信号", "需求时机"],
  },
];

export const promptExplorerFaqs: PromptFaqItem[] = resolveSiteCopyDeep([
  {
    number: "01",
    label: "定义",
    question: "什么是查询扇出？",
    paragraphs: [
      "查询扇出指的是 AI 在回答一个问题时，为生成最终答案所展开的研究路径，包括拆解出的子查询数量以及引用的信息来源数量。",
      "在 {{name}} 中，查询扇出基于 RAG（检索增强生成）架构和多智能体工作流，模拟 AI 的查询拆解与并行检索过程，记录子查询数量、引用来源及趋势变化，真实还原 AI 的研究路径。",
    ],
  },
  {
    number: "02",
    label: "重要性",
    question: "查询扇出越高代表什么？",
    paragraphs: [
      "查询扇出越高，说明 AI 需要拆解更多子问题并参考更多来源，问题背后的研究深度与决策复杂度也更高。",
      "在 {{name}} 中，高扇出主题通常意味着更高的决策价值。如果品牌在这些问题中的引用率较低，往往是优先布局的关键机会。",
    ],
  },
  {
    number: "03",
    label: "区别",
    question: "提示词与查询扇出和关键词分析有什么不同？",
    paragraphs: [
      "关键词分析关注「用户搜索什么」；查询扇出关注「AI 如何研究问题」。",
      "{{name}} 通过模拟 AI 的拆解与检索流程，展示子查询结构、引用来源分布及平台差异，让你看到的不只是搜索量，而是 AI 的决策链路。",
    ],
  },
  {
    number: "04",
    label: "应用",
    question: "如何利用查询扇出找到高价值机会？",
    paragraphs: [
      "高价值机会通常是「高扇出 + 低品牌引用」的提示词。",
      "{{name}} 会自动识别这些研究深度高但品牌缺席的场景，帮助你优先布局内容与产品页面，提高在 AI 回答链路中的可见度与引用概率。",
    ],
  },
  {
    number: "05",
    label: "决策",
    question: "查询扇出可以帮助我做哪些决策？",
    paragraphs: [
      "查询扇出可用于判断问题是否值得投入、制定内容与 GEO 优先级，以及提前预判用户的下一步提问方向，帮助品牌在 AI 回答链路中提前占位。",
    ],
  },
]);

export const promptExplorerCta: CtaContent = resolveSiteCopyDeep({
  badge: "准备就绪",
  titleBefore: "准备好查看用户在 AI 中",
  titleHighlight: "问了什么",
  titleAfter: "吗？",
  description: "加入 {{name}}，共同追踪 AI 搜索可见度。基于数据洞察，告别盲目优化。",
  codeLines: ["// 停止猜测。", "// 开始掌控。"],
  secondaryCtaLabel: "登录",
  secondaryCtaHref: "/auth/login",
  primaryCtaLabel: "开始试用",
  primaryCtaHref: "/auth/register",
});
