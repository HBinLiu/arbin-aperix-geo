import type { PlatformId } from "../platform";

/** 单页默认 SEO（title 为主题，不含 `| 品牌名`；description 可含 {{siteName}}） */
export type PageSeoDefault = {
  label: string;
  path: string;
  titleTopic: string;
  description: string;
  noindex?: boolean;
};

export type MonitorPageSeoDefault = PageSeoDefault & {
  platformId: PlatformId;
};

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
} as const satisfies Record<string, PageSeoDefault>;

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

export const SOLUTION_TEAM_SEO = {
  agencies: {
    label: "代理商",
    path: "/solution/agencies/",
    titleTopic: "面向代理商：规模化多品牌 AI 管理解决方案",
    description:
      "在一个平台管理所有客户的 AI 可见性。白标仪表盘、批量报告和团队权限。无需招聘新专家即可扩展 GEO 业务。",
  },
  enterprise: {
    label: "大型企业",
    path: "/solution/enterprise/",
    titleTopic: "面向大型企业团队：AI 品牌影响力与信任建设策略",
    description:
      "面向大型组织的战略平台，旨在提升 AI 品牌影响力和信任度。高管仪表盘、定制集成和专属支持，助力品牌主导地位。",
  },
  "pr-brand-teams": {
    label: "公关与品牌团队",
    path: "/solution/pr-brand-teams/",
    titleTopic: "面向公关与品牌团队：塑造 AI 对话中的品牌形象",
    description:
      "跨 AI 平台监控品牌声誉。追踪情感、竞争定位并塑造叙事。实时危机检测和声誉管理。",
  },
  "smb-geo-teams": {
    label: "中小企业 GEO 团队",
    path: "/solution/smb-geo-teams/",
    titleTopic: "面向中小企业团队：提升 AI 可见性并构建品牌信任",
    description:
      "面向小团队的简单、实惠的 GEO 平台。快速 AI 就绪诊断、一键监控和可落地建议。无需 GEO 专家。",
  },
  "seo-specialists": {
    label: "SEO 专家",
    path: "/solution/seo-specialists/",
    titleTopic: "面向 SEO 从业者 - 高性价比且专业的 GEO 优化工具",
    description:
      "专为独立 SEO 顾问打造的实惠 GEO 平台。AI 可见性追踪、竞争分析和报告工具。以低成本最大化客户价值。",
  },
} as const satisfies Record<string, PageSeoDefault>;

export const SCENE_SEO = {
  "product-launch": {
    label: "产品发布",
    path: "/scene/product-launch/",
    titleTopic: "AI 新品冷启动发布策略 - 上线首日即获 AI 引用",
    description:
      "确保新产品从发布首日就被 AI 发现和引用。发布前规划、发布日战术和发布后加速，实现即时 AI 可见性。",
  },
  "narrative-shaping": {
    label: "叙事构建",
    path: "/scene/narrative-shaping/",
    titleTopic: "塑造您的品牌叙事 - 掌控 AI 如何推荐您",
    description:
      "主动影响 AI 平台如何呈现和推荐您的品牌。叙事影响力的三个层级：直接、放大和生态系统策略。",
  },
  "content-strategy": {
    label: "内容策略",
    path: "/scene/content-strategy/",
    titleTopic: "面向 AI 内容策略 - 构建 AI 主动转述的品牌叙事",
    description:
      "跨 AI 平台构建一致的品牌叙事。开发包含问题支柱、解决方案方法论和证据内容的整合内容策略，以建立 AI 信任。",
  },
  "competitive-positioning": {
    label: "竞争定位",
    path: "/scene/competitive-positioning/",
    titleTopic: "抢占 AI 搜索市场份额 - 竞争定位与差异化分析",
    description:
      "了解您在 AI 推荐中与竞争对手的对比情况。识别差距，发现机会，并执行策略以在 AI 中主导您的品类。",
  },
  "brand-crisis-management": {
    label: "品牌危机管理",
    path: "/scene/brand-crisis-management/",
    titleTopic: "AI 品牌危机管理 - 实时声誉保护",
    description:
      "实时监控并响应负面 AI 提及。检测声誉风险，分析情感，并执行修正性内容策略以保护品牌信任。",
  },
} as const satisfies Record<string, PageSeoDefault>;

/** @deprecated 使用 `SCENE_SEO` */
export const SOLUTION_USE_CASE_SEO = SCENE_SEO;

export const MONITOR_PAGE_SEO: Record<PlatformId, MonitorPageSeoDefault> = {
  doubao: {
    platformId: "doubao",
    label: "豆包监测",
    path: "/platform/we-monitor-doubao/",
    titleTopic: "豆包优化 - 监控 AI 搜索排名",
    description: "掌握豆包对中文内容与字节生态的引用偏好，监测并优化品牌在豆包中的 AI 可见性。",
  },
  deepseek: {
    platformId: "deepseek",
    label: "DeepSeek 监测",
    path: "/platform/we-monitor-deepseek/",
    titleTopic: "DeepSeek 优化 - 监控 AI 搜索排名",
    description:
      "掌握 DeepSeek 对技术与学术内容的引用偏好，监测并优化品牌在 DeepSeek 中的 AI 可见性。",
  },
  qianwen: {
    platformId: "qianwen",
    label: "通义千问监测",
    path: "/platform/we-monitor-qwen/",
    titleTopic: "通义千问优化 - 监控 AI 搜索排名",
    description: "掌握通义千问对中文内容的引用偏好，优化品牌在阿里 AI 生态中的可见性。",
  },
  yuanbao: {
    platformId: "yuanbao",
    label: "腾讯元宝监测",
    path: "/platform/we-monitor-yuanbao/",
    titleTopic: "腾讯元宝优化 - 监控 AI 搜索排名",
    description:
      "掌握腾讯元宝对中文内容与微信生态的引用偏好，监测并优化品牌在元宝中的 AI 可见性。",
  },
  kimi: {
    platformId: "kimi",
    label: "Kimi 监测",
    path: "/platform/we-monitor-kimi/",
    titleTopic: "Kimi 优化 - 监控 AI 搜索排名",
    description: "掌握 Kimi 对长文本与专业内容的引用偏好，监测并优化品牌在 Kimi 中的 AI 可见性。",
  },
  ernie: {
    platformId: "ernie",
    label: "文心一言监测",
    path: "/platform/we-monitor-ernie/",
    titleTopic: "文心一言优化 - 监控 AI 搜索排名",
    description:
      "掌握文心一言对中文内容与百度搜索生态的引用偏好，监测并优化品牌在文心一言中的 AI 可见性。",
  },
};

export const SITE_NAME_PLACEHOLDER = "{{siteName}}";

/** Payload `page-seo` collection 的 meta.title 格式 */
export function cmsPageSeoTitle(titleTopic: string): string {
  return `${titleTopic} | ${SITE_NAME_PLACEHOLDER}`;
}

export type CmsPageSeoSeedEntry = {
  label: string;
  path: string;
  meta: {
    title: string;
    description: string;
  };
  noindex?: boolean;
};

export function toCmsPageSeoSeed(defaults: PageSeoDefault): CmsPageSeoSeedEntry {
  return {
    label: defaults.label,
    path: defaults.path,
    meta: {
      title: cmsPageSeoTitle(defaults.titleTopic),
      description: defaults.description,
    },
    noindex: defaults.noindex,
  };
}

/** Payload seed 写入 `page-seo` collection 的全量默认条目 */
export const defaultPageSeoEntries: CmsPageSeoSeedEntry[] = [
  toCmsPageSeoSeed(CORE_PAGE_SEO.home),
  toCmsPageSeoSeed(CORE_PAGE_SEO.about),
  toCmsPageSeoSeed(CORE_PAGE_SEO.contact),
  toCmsPageSeoSeed(CORE_PAGE_SEO.pricing),
  ...Object.values(PLATFORM_PAGE_SEO).map(toCmsPageSeoSeed),
  ...Object.values(SOLUTION_TEAM_SEO).map(toCmsPageSeoSeed),
  ...Object.values(MONITOR_PAGE_SEO).map(toCmsPageSeoSeed),
];
