import type { ComparisonRow, FeatureItem } from "./payload";
import { HERO_PLATFORM_IDS } from "@shared/platform";

export type HeroHeadlinePart =
  | { type: "text"; content: string }
  | { type: "focus"; content: string };

export type HeroContent = {
  eyebrow?: string;
  headline?: HeroHeadlinePart[];
  description?: string;
  inputPlaceholder?: string;
  primaryCtaLabel?: string;
  primaryCtaHref?: string;
};

export type FeaturesContent = {
  titleLine1?: string;
  titleLine2Before?: string;
  titleHighlight?: string;
  titleLine2After?: string;
  items: FeatureItem[];
};

export type FaqItem = {
  question: string;
  answer: string;
};

export type CtaContent = {
  badge: string;
  titleBefore: string;
  titleHighlight: string;
  titleAfter: string;
  description: string;
  codeLines: string[];
  secondaryCtaLabel: string;
  secondaryCtaHref: string;
  primaryCtaLabel: string;
  primaryCtaHref: string;
};

export type DiagnosticContent = {
  eyebrow: string;
  titleLine1: string;
  titleLine2Suffix: string;
  rotatingHighlights: string[];
  ctaLabel: string;
  ctaHref: string;
};

/** 首页静态文案与区块数据（不来自 Payload） */
export const homeHero: HeroContent = {
  eyebrow: "实时监测这些 AI 引擎中的品牌提及",
  headline: [
    { type: "text", content: "你的" },
    { type: "focus", content: "品牌" },
    { type: "text", content: "，正在被 AI" },
    { type: "focus", content: "遗忘" },
    { type: "text", content: "吗？" },
  ],
  description: "专为企业 AI 营销打造，不只是监测数据——把 AI 可见性转化为真实商机。",
  inputPlaceholder: "输入你的品牌/官网，获取品牌 AI 曝光诊断报告",
  primaryCtaLabel: "获取诊断报告",
  primaryCtaHref: "/auth/register",
};

export const homePlatforms = [...HERO_PLATFORM_IDS];

export const homeDiagnostic: DiagnosticContent = {
  eyebrow: "「 运行一次品牌诊断 」",
  titleLine1: "想知道你在",
  titleLine2Suffix: "中的表现吗？",
  rotatingHighlights: ["豆包", "DeepSeek", "千问", "元宝", "Kimi", "文心一言"],
  ctaLabel: "生成诊断报告",
  ctaHref: "/auth/register",
};

export const homeFeatures: FeaturesContent = {
  titleLine1: "AI 有没有提到你、推荐你？",
  titleLine2Before: "理解",
  titleHighlight: "原因",
  titleLine2After: "，快人一步！",
  items: [
    {
      phase: "SEE",
      code: "监测",
      title: "你在 AI 世界里的实时地图",
      titleBefore: "你在 AI",
      titleHighlight: " 世界 ",
      titleAfter: "里的实时地图",
      tagline: "关键指标：提及频次 · 引用率 · 竞品对比 · 时间窗口",
      pain: "你不知道当用户问 AI 时，你的品牌有没有被提及、被推荐。",
      solution: "{{name}} 支持国内 6 大主流 AI 平台，给你一张实时的 AI 曝光热力图。",
      metrics: ["可见度", "提及频次", "声量份额", "竞品对比"],
      image: "panel-1",
    },
    {
      phase: "UNDERSTAND",
      code: "分析",
      title: "AI 引用了谁，你才能知道该做什么",
      titleBefore: "AI ",
      titleHighlight: "引用了谁",
      titleAfter: "，你才能知道该做什么",
      tagline: "反向解析回答背后的引用来源与情感位次",
      pain: "知道被提及了没用，知道 AI 为什么提到你、引用了哪些来源才有用。",
      solution: "反向解析 AI 回答背后的引用来源，告诉你哪些内容/网站正在替你说话——或者在帮竞品抢你的位置。",
      metrics: ["引用来源", "情感倾向", "排名变化", "证据链"],
      image: "panel-2",
    },
    {
      phase: "ACT",
      code: "行动",
      title: "用数据驱动复盘，而不是凭感觉改内容",
      titleBefore: "用",
      titleHighlight: " 数据驱动 ",
      titleAfter: "复盘，而不是凭感觉改内容",
      tagline: "聚合视图支撑内部分享与迭代决策",
      pain: "有了数据，不知道该改哪里、怎么改。",
      solution: "{{name}} 直接告诉你该写什么、怎么写、帮你写——不只是建议，是可以直接用的内容。",
      metrics: ["任务聚合", "主体对比", "提示词版本", "导出复盘"],
      image: "panel-3",
    },
  ],
};

export const homeComparison = {
  titleBefore: "为什么选择 ",
  titleHighlight: "{{name}}",
  titleAfter: "？",
  rows: [
    {
      dimension: "定位",
      aperix: "看见 → 读懂 → 行动，一套闭环",
      lightweight: "看基础数据，深挖分析靠你自己",
      enterprise: "数据复杂，采购成本高",
    },
    {
      dimension: "入门价格",
      aperix: "299元起，核心功能全开",
      lightweight: "199元起，单模型支持",
      enterprise: "千元起步，关键功能分层锁定",
    },
    {
      dimension: "证据回溯",
      aperix: "保留完整回答、引用与解析结果",
      lightweight: "Playwright 技术，取证不稳定",
      enterprise: "大部分需企业档才能使用",
    },
    {
      dimension: "模型覆盖",
      aperix: "覆盖国内6大主流模型",
      lightweight: "选择 2–4 个基础模型",
      enterprise: "仅需要企业档才能全覆盖",
    },
    {
      dimension: "内容创作",
      aperix: "品牌知识库，输出高质量内容",
      lightweight: "不支持",
      enterprise: "内容生成有限，质量偏弱",
    },
    {
      dimension: "代理商/OEM",
      aperix: "灵活OEM模式，低成本高效获客",
      lightweight: "不支持",
      enterprise: "仅高价合同支持",
    },
    {
      dimension: "上手难度",
      aperix: "快速上手，功能完整",
      lightweight: "简单，但能做的有限",
      enterprise: "复杂，学习曲线陡峭",
    },
    {
      dimension: "响应速度",
      aperix: "最快 2H 及时响应",
      lightweight: "无官方承诺",
      enterprise: "仅企业档支持",
    },
  ] satisfies ComparisonRow[],
};

export const homeCta: CtaContent = {
  badge: "准备就绪",
  titleBefore: "准备好发现你与竞争对手之间的",
  titleHighlight: "可见性差距",
  titleAfter: "了吗？",
  description: "加入 {{name}}，追踪 AI 可见性。获得基于实战的深度洞察，告别盲目猜测。",
  codeLines: ["// 停止猜测。", "// 开始掌控。"],
  secondaryCtaLabel: "登录",
  secondaryCtaHref: "/auth/login",
  primaryCtaLabel: "开始试用",
  primaryCtaHref: "/auth/register",
};

export const homeFaqs: FaqItem[] = [
  {
    question: "GEO 和 SEO 有什么区别？",
    answer:
      "SEO 针对搜索引擎排名进行优化。GEO（生成引擎优化）针对 AI 模型的引用和推荐进行优化。两者对于全面的品牌可见性都至关重要。",
  },
  {
    question: "{{name}} 与其他 GEO 工具有什么不同？",
    answer:
      "我们关注信任，而不仅仅是可见性。我们为您展示排名位置、情感分析和可执行的建议，而不仅仅是提及次数。",
  },
  {
    question: "支持哪些 AI 模型？",
    answer:
      "国内主流大模型：豆包、DeepSeek、通义千问、腾讯元宝、Kimi、文心一言均已支持 —— 更多模型正在持续添加中。",
  },
  {
    question: "多久能看到效果？",
    answer:
      "趋势可见性需要 2-4 周，可落地洞察需要 4-8 周。AI 模型的更新速度与搜索引擎不同。我们同样也提供针对中大型企业的GEO/SEO优化服务，帮助您直接达成流量/AI可见度的目标，直接交付结果。",
  },
];
