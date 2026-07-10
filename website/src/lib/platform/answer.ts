import type { CtaContent } from "@/lib/home";
import type { PlatformFaqItem } from "@/lib/platform/faq";
import insightsVideo from "@shared/assets/videos/website/answer-insight.webm";

export const INSIGHTS_VIDEO_URL = insightsVideo;

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

export type InsightsFaqItem = PlatformFaqItem;

export const answerEngineInsightsHero = {
  titleBefore: "了解 AI 如何回答关于",
  titleHighlight: "你品牌",
  titleAfter: "的问题",
  tagline: "看清你的品牌在 AI 回答中的真实位置，以及缺失的机会点",
  description:
    "监测您的品牌可见度、提及量和声量份额在人工智能生成的答案中的变化。让您了解自身所处的位置、与竞争对手的差距以及下一步的优化方向。",
  primaryCtaLabel: "获取演示",
  primaryCtaHref: "/auth/register",
  secondaryCtaLabel: "立即开始",
  secondaryCtaHref: "/auth/register",
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

export const answerEngineInsightsFaqs: InsightsFaqItem[] = [
  {
    number: "01",
    label: "方法",
    question: "{{name}} 是如何分析 AI 是如何「回答」我的品牌的？",
    paragraphs: [
      "{{name}} 基于真实 AI 平台（如豆包、DeepSeek、通义千问等）的实际输出结果，系统化追踪品牌在 AI 回答中的可见度、提及方式、排序位置与引用来源等。",
      "这不是模拟或预测，而是对 AI 在真实用户提问场景中如何理解、引用与呈现你的品牌的真实还原，从而帮助你判断当前 AI 对品牌的实际认知状态。",
    ],
  },
  {
    number: "02",
    label: "差异",
    question: "AI 可见度数据和传统 SEO 排名有什么不同？",
    paragraphs: [
      "传统 SEO 关注的是网页在搜索结果中的位置，而 AI 可见度关注的是：在 AI 直接给出的答案里，是否提到你、如何提到你、是否引用你。",
      "{{name}} 分析的是 AI Answer 层的表现，包括 Visibility、Share of Voice、Citation 和情绪倾向等，帮助您理解在 AI 搜索与问答场景中，品牌是否真正「被看见、被信任、被推荐」。",
    ],
  },
  {
    number: "03",
    label: "竞争",
    question: "我可以看到和竞争对手在同一个 AI 问题下的对比吗？",
    paragraphs: [
      "可以。{{name}} 基于真实用户 Prompt，在同一个问题场景中，直观展示您与竞争对手的是否被 AI 提及、出现顺位、声量份额与引用来源差异。",
      "这能帮助您快速识别：哪些高价值问题已经被对手占据，哪些仍是可突破的机会点。",
    ],
  },
  {
    number: "04",
    label: "引用",
    question: "AI 引用我的品牌时，依赖的是哪些网站或内容？",
    paragraphs: [
      "{{name}} 会拆解 AI 回答背后的引用来源结构，包括引用的具体域名与页面、内容类型（官网、博客、新闻、社媒、电商 / 购物平台等），以及不同 AI 平台的引用偏好差异。",
      "通过这些洞察，您可以明确：哪些内容正在影响 AI 的判断逻辑，以及哪些引用入口是可以被补齐、替代或强化的。",
    ],
  },
  {
    number: "05",
    label: "行动",
    question: "{{name}} 的数据能直接指导我接下来该怎么优化吗？",
    paragraphs: [
      "可以，而且这是核心价值之一。{{name}} 不仅展示结果，还会帮助您识别 AI 偏好的内容结构与主题方向，判断 GEO 资源该优先投向哪些平台、问题或页面，并提前发现潜在的负面情绪或认知偏差风险。",
      "让您从「看到差距」，进一步走到「知道下一步该做什么」。",
    ],
  },
];

export const answerEngineInsightsCta: CtaContent = {
  badge: "准备就绪",
  titleBefore: "准备好查看你品牌的",
  titleHighlight: "信任分",
  titleAfter: "了吗？",
  description: "加入 {{name}}，共同追踪 AI 搜索可见度。基于数据洞察，告别盲目优化。",
  codeLines: ["// 停止猜测。", "// 开始掌控。"],
  secondaryCtaLabel: "登录",
  secondaryCtaHref: "/auth/login",
  primaryCtaLabel: "开始试用",
  primaryCtaHref: "/auth/register",
};
