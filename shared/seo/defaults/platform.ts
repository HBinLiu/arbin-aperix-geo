import type { PageSeoDefault } from "./types";

export const PLATFORM_PAGE_SEO = {
  answer: {
    label: "回答引擎洞察",
    path: "/platform/answer-engine-insights/",
    titleTopic: "AI 可见度与竞争洞察分析",
    description:
      "基于真实 AI 回答与 Prompt，分析品牌在 AI 搜索中的可见度、声量份额与引用结构，识别竞争差距与高价值优化机会。",
  },
  topics: {
    label: "发现机会与差距",
    path: "/platform/find-topics-ideas/",
    titleTopic: "AI 增长机会与信源分析",
    description:
      "基于真实提示词与引用结构，识别尚未覆盖的高价值场景与信源机会，将 AI 回答逻辑转化为可执行的 GEO 增长策略。",
  },
  prompt: {
    label: "提示词查询探索",
    path: "/platform/prompt-volumes-explorer/",
    titleTopic: "提示词与查询扇出分析",
    description:
      "分析真实提示词与查询扇出，洞察 AI 如何拆解用户需求，识别高价值问题与趋势变化，优化内容与 GEO 投入优先级。",
  },
  content: {
    label: "内容创作与优化",
    path: "/platform/content-creation-optimization/",
    titleTopic: "AI 智能内容创作引擎",
    description:
      "创作针对搜索引擎和 AI 平台创作的高质量文章。内置 SEO/GEO 优化的内容简报、大纲和完整文章。",
  },
} as const satisfies Record<string, PageSeoDefault>;
