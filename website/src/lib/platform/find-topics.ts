import type { CtaContent } from "@/lib/home";
import type { PageSeo } from "@/lib/seo";
import findTopicsIdeaVideo from "@shared/assets/videos/website/find-topics-idea.webm";

export const FIND_TOPICS_IDEAS_PATH = "/platform/find-topics-ideas";

export const FIND_TOPICS_VIDEO_URL = findTopicsIdeaVideo;

export type FindTopicsFeatureIcon = "content" | "social" | "citation" | "commerce";

export type FindTopicsFeature = {
  icon: FindTopicsFeatureIcon;
  title: string;
  bullets: string[];
  tags: string[];
};

export type FindTopicsFaqItem = {
  number: string;
  label: string;
  question: string;
  paragraphs: string[];
  bullets?: string[];
  closingParagraphs?: string[];
};

export const findTopicsIdeasSeo: PageSeo = {
  title: "AI 增长机会与信源分析 | Aperix AI",
  description:
    "基于真实提示词与引用结构，识别尚未覆盖的高价值场景与信源机会，将 AI 回答逻辑转化为可执行的 GEO 增长策略。",
};

export const findTopicsIdeasHero = {
  titleBefore: "将 AI 回答转化为可执行的",
  titleHighlight: "机会",
  titleAfter: "",
  tagline: "看懂 AI 如何判断品牌，以及真正的增长机会从哪里出现",
  description:
    "通过分析竞品、真实提示词与引用结构，帮助您识别尚未被充分覆盖的高价值场景、被竞争对手忽视的问题，以及能够快速建立优势的关键位置。将 AI 的判断逻辑，直接转化为可执行的增长机会。",
  primaryCtaLabel: "获取演示",
  primaryCtaHref: "/auth/register",
  secondaryCtaLabel: "立即开始",
  secondaryCtaHref: "/auth/register",
};

export const findTopicsIdeasFeaturesHeader = {
  titleBefore: "识别真正的",
  titleHighlight: "机会所在",
  description: "在内容、社区、信源和电商等场景中，找出真正有价值的机会缺口。",
};

export const findTopicsIdeasFeatures: FindTopicsFeature[] = [
  {
    icon: "content",
    title: "内容覆盖分析",
    bullets: [
      "对比品牌与竞品在 AI 回答中的覆盖深度与排名，找出潜在切入点。",
      "通过真实提示词还原 AI 回答逻辑，发现尚未被占据的高价值问答场景。",
    ],
    tags: ["AI 可见性", "AI 排名", "内容机会"],
  },
  {
    icon: "social",
    title: "社媒与社区洞察",
    bullets: [
      "分析社交媒体平台、问答社区和在线论坛中的热门话题、用户关注点及讨论模式，揭示最能引起受众参与的内容。",
      "挖掘品牌未覆盖的讨论区和互动机会，为内容布局提供线索。",
    ],
    tags: ["话题趋势洞察", "社区内容机会"],
  },
  {
    icon: "citation",
    title: "信源与外链机会",
    bullets: [
      "审视 AI 回答引用的域名和页面类型，发现被忽略的高价值信源。",
      "区分新闻网站、行业门户、博客等外链资源，结合行业领域分析引用偏好。",
    ],
    tags: ["引用来源", "域名信号", "新闻", "行业"],
  },
  {
    icon: "commerce",
    title: "电商与产品场景分析",
    bullets: [
      "发现 AI 易引用的商品提示词，找出用户关注的产品场景。",
      "分析产品在不同平台、不同区域的表现，识别高潜力市场。",
    ],
    tags: ["产品提示词", "市场洞察", "+128%"],
  },
];

export const findTopicsIdeasFaqs: FindTopicsFaqItem[] = [
  {
    number: "01",
    label: "方法论",
    question: "Aperix AI 是如何识别 AI 机会？",
    paragraphs: [
      "Aperix AI 并不是基于假设或关键词预测，而是基于真实 AI 回答、真实提示词和真实引用结构进行分析。",
      "我们通过对比品牌与竞争对手在 AI 回答中的覆盖深度、排序位置和引用来源等信息，识别：",
    ],
    bullets: [
      "尚未被充分覆盖的高价值问题",
      "被竞争对手忽视但 AI 明确偏好的场景",
      "能够快速建立 AI 可见度优势的切入点",
    ],
    closingParagraphs: ["让机会来自 AI 的实际判断逻辑，而不是主观推测。"],
  },
  {
    number: "02",
    label: "竞争",
    question: "能看到被竞品占据的机会吗？",
    paragraphs: [
      "可以，而且这是 Aperix AI 的核心能力之一。",
      "平台会清晰展示：",
    ],
    bullets: [
      "在哪些提示词下，AI 已经频繁引用竞争对手",
      "竞争对手依赖的是哪些内容、信源或外链",
      "当前品牌在哪些高价值场景中仍然「缺席」",
    ],
    closingParagraphs: [
      "这些洞察可以直接指导用户：优先补什么内容、先抢哪个问题、从哪里切入最容易见效。",
    ],
  },
  {
    number: "03",
    label: "覆盖范围",
    question: "Aperix AI 的机会分析涵盖社交媒体、电子商务和社区场景吗？",
    paragraphs: [
      "可以。Aperix AI 不只分析官网和博客，还会系统性拆解 AI 回答中引用的：社交媒体内容、问答社区与论坛、电商平台和产品页面。",
      "通过这些分析，你可以发现：",
    ],
    bullets: [
      "哪些社区讨论正在影响 AI 的判断",
      "哪些产品场景和提示词更容易被 AI 推荐",
      "哪些平台和区域具备更高的增长潜力",
    ],
    closingParagraphs: ["从而把 GEO 机会延伸到内容、社媒、电商和增长协同。"],
  },
  {
    number: "04",
    label: "执行",
    question: "在发现机会后，Aperix AI 能否帮我真正「执行」？",
    paragraphs: [
      "可以。Aperix AI 的目标不是只告诉你「机会在哪」，而是帮助你把机会转化为可衡量的增长，包括：",
    ],
    bullets: [
      "基于高价值提示词直接生成内容",
      "明确哪些外链和信源最值得优先投入",
      "持续监控机会是否转化为 AI 可见度和引用提升",
    ],
    closingParagraphs: ["让每一次优化，都围绕 AI 是否真的开始更多地提及你。"],
  },
  {
    number: "05",
    label: "可扩展性",
    question: "Aperix AI 的机会是否适合大规模执行而非一次性优化？",
    paragraphs: [
      "是的。Aperix AI 将机会设计为可复制、可扩展的增长单元，而不是单点建议。",
      "当某一类提示词、内容结构或信源类型被验证有效后，你可以将同样的逻辑快速扩展到：",
    ],
    bullets: ["更多相似问题", "不同平台或区域", "不同产品线或解决方案"],
    closingParagraphs: [
      "这使得优化不再是零散动作，而是可以持续放大的系统性增长策略。",
    ],
  },
];

export const findTopicsIdeasCta: CtaContent = {
  badge: "准备就绪",
  titleBefore: "准备好查看用户在 AI 中",
  titleHighlight: "问了什么",
  titleAfter: "吗？",
  description: "加入 Aperix AI，共同追踪 AI 搜索可见度。基于数据洞察，告别盲目优化。",
  codeLines: ["// 停止猜测。", "// 开始掌控。"],
  secondaryCtaLabel: "登录",
  secondaryCtaHref: "/auth/login",
  primaryCtaLabel: "开始试用",
  primaryCtaHref: "/auth/register",
};
