import type { CtaContent } from "@/lib/home";
import { resolveSiteCopyDeep } from "@/lib/site";
import type { Faq } from "@/lib/platform/faq";
import { findTopicsIdeasFaqDefaults } from "@shared/faq/defaults";
import { mergeFaqs, resolveFaqDefaults } from "@/lib/faqs";
import type { FaqDoc } from "@shared/faq";
import findTopicsIdeaVideo from "@shared/assets/videos/website/find-topics-idea.webm";

export const FIND_TOPICS_VIDEO_URL = findTopicsIdeaVideo;

export type FindTopicsFeatureIcon = "content" | "social" | "citation" | "commerce";

export type FindTopicsFeature = {
  icon: FindTopicsFeatureIcon;
  title: string;
  bullets: string[];
  tags: string[];
};

export const findTopicsIdeasFaqs: Faq[] = resolveFaqDefaults(findTopicsIdeasFaqDefaults);

export function mergeFindTopicsIdeasFaqs(cms: FaqDoc[] | null | undefined): Faq[] {
  return mergeFaqs(cms, findTopicsIdeasFaqs);
}

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

export const findTopicsIdeasCta: CtaContent = resolveSiteCopyDeep({
  badge: "准备就绪",
  titleBefore: "准备好查看用户在 AI 中",
  titleHighlight: "问了什么",
  titleAfter: "吗？",
  description: "加入 {{siteName}}，共同追踪 AI 搜索可见度。基于数据洞察，告别盲目优化。",
  codeLines: ["// 停止猜测。", "// 开始掌控。"],
  secondaryCtaLabel: "登录",
  secondaryCtaHref: "/auth/login",
  primaryCtaLabel: "开始试用",
  primaryCtaHref: "/auth/register",
});
