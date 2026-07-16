import type { PageSeoDefault } from "./types.ts";

export const CORE_PAGE_SEO = {
  home: {
    label: "首页",
    path: "/",
    titleTopic: "数据驱动的 GEO 品牌可见性监测平台",
    description:
      "{{siteName}} 专注于生成式引擎优化，覆盖国内主流大模型平台，监测品牌在 AI 中的可见度以及竞争洞察分析。不止于 GEO 审计，更提供数据驱动的 GEO 增长策略、AI 内容创作引擎与优化服务。",
  },
  about: {
    label: "关于我们",
    path: "/about/",
    titleTopic: "关于我们",
    description:
      "{{siteName}} 是一家专注于生成式引擎优化的公司，致力于帮助品牌建立真实的 AI 信任与影响力。我们连接 SEO 与 GEO，让每个企业都能获得 AI 可见性，更提供数据驱动的 GEO 增长策略、AI 内容创作引擎与优化服务。。",
  },
  contact: {
    label: "联系我们",
    path: "/contact/",
    titleTopic: "预约演示 - 了解平台实际效果",
    description:
      "预约一对一产品演示，与 {{siteName}} 专家交流，了解如何优化 AI 搜索可见性并获得定制化建议。",
  },
  pricing: {
    label: "定价",
    path: "/pricing/",
    titleTopic: "定价方案",
    description:
      "覆盖国内主流 AI 平台的订阅方案。个人版、专业版、旗舰版与企业版，按月/季/年灵活订阅。",
  },
  research: {
    label: "研究",
    path: "/research/",
    titleTopic: "研究 - AI 搜索市场报告与数据",
    description:
      "获取关于 AI 搜索趋势的原创研究报告与市场数据。洞察 GEO 策略、AI 用户行为以及新兴的营销机会。",
  },
  news: {
    label: "新闻",
    path: "/news/",
    titleTopic: "新闻 - 每周 AI 与产品动态",
    description:
      "汇总每周 AI 新闻、产品发布、模型更新与生态变化，帮助运营和营销团队快速掌握行业重点。",
  },
  blog: {
    label: "博客",
    path: "/blog/",
    titleTopic: "博客 - AI 可见性实践与 GEO 洞察",
    description:
      "由实战经验驱动的 AI 可见性、GEO 与 SEO 实践文章，帮助营销与内容团队落地可执行策略。",
  },
  academy: {
    label: "学院",
    path: "/academy/",
    titleTopic: "学院 - GEO 与 SEO 运营指南",
    description:
      "系统化的 GEO 与 SEO 指南，帮助团队掌握 AI 搜索可见性策略、内容实践与落地方法。",
  },
} as const satisfies Record<string, PageSeoDefault>;
