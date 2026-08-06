/** FAQ `page` 字段取值（Payload 与 website 共用） */

export const FAQ_PAGE = {
  home: "home",
  pricing: "pricing",
  platformAnswer: "platform/answer-engine-insights",
  platformTopics: "platform/find-topics-ideas",
  platformPrompt: "platform/prompt-volumes-explorer",
  platformContent: "platform/content-creation-optimization",
  singlePageAudit: "free-tools/single-page-audit",
  llmsTxtGenerator: "free-tools/llms-txt-generator",
  hotPromptFinder: "free-tools/hot-prompt-finder",
  geoWebsite: "services/geo-website",
} as const;

export const TEAM_SOLUTION_SLUGS = [
  "agencies",
  "enterprise",
  "pr-brand-teams",
  "smb-geo-teams",
  "seo-specialists",
] as const;

export const SCENE_SLUGS = [
  "brand-crisis-management",
  "competitive-positioning",
  "content-strategy",
  "narrative-shaping",
  "product-launch",
] as const;

/** @deprecated 使用 `SCENE_SLUGS` */
export const USE_CASE_SOLUTION_SLUGS = SCENE_SLUGS;

export type TeamSolutionSlug = (typeof TEAM_SOLUTION_SLUGS)[number];
export type SceneSlug = (typeof SCENE_SLUGS)[number];
/** @deprecated 使用 `SceneSlug` */
export type UseCaseSolutionSlug = SceneSlug;
export type SolutionSlug = TeamSolutionSlug | SceneSlug;

export const MONITOR_FAQ_SLUGS = [
  "we-monitor-doubao",
  "we-monitor-deepseek",
  "we-monitor-qwen",
  "we-monitor-yuanbao",
  "we-monitor-kimi",
  "we-monitor-ernie",
] as const;

export type MonitorFaqSlug = (typeof MONITOR_FAQ_SLUGS)[number];
export type MonitorFaqPageKey = `monitor/${MonitorFaqSlug}`;

export type TeamSolutionFaqPageKey = `solution/${TeamSolutionSlug}`;
export type SceneFaqPageKey = `scene/${SceneSlug}`;
export type FaqPageKey =
  | (typeof FAQ_PAGE)[keyof typeof FAQ_PAGE]
  | MonitorFaqPageKey
  | TeamSolutionFaqPageKey
  | SceneFaqPageKey;

export function monitorFaqPage(slug: MonitorFaqSlug): MonitorFaqPageKey {
  return `monitor/${slug}`;
}

export function teamSolutionFaqPage(slug: TeamSolutionSlug): TeamSolutionFaqPageKey {
  return `solution/${slug}`;
}

export function sceneFaqPage(slug: SceneSlug): SceneFaqPageKey {
  return `scene/${slug}`;
}

export const FAQ_PAGE_OPTIONS = [
  { label: "首页", value: FAQ_PAGE.home },
  { label: "定价", value: FAQ_PAGE.pricing },
  { label: "回答引擎洞察", value: FAQ_PAGE.platformAnswer },
  { label: "发现机会与差距", value: FAQ_PAGE.platformTopics },
  { label: "提示词查询探索", value: FAQ_PAGE.platformPrompt },
  { label: "内容创作与优化", value: FAQ_PAGE.platformContent },
  { label: "单页审计", value: FAQ_PAGE.singlePageAudit },
  { label: "LLMs.txt 生成器", value: FAQ_PAGE.llmsTxtGenerator },
  { label: "热门提示词发现器", value: FAQ_PAGE.hotPromptFinder },
  { label: "官网定制服务", value: FAQ_PAGE.geoWebsite },
  { label: "豆包监测", value: monitorFaqPage("we-monitor-doubao") },
  { label: "DeepSeek 监测", value: monitorFaqPage("we-monitor-deepseek") },
  { label: "通义千问监测", value: monitorFaqPage("we-monitor-qwen") },
  { label: "腾讯元宝监测", value: monitorFaqPage("we-monitor-yuanbao") },
  { label: "Kimi 监测", value: monitorFaqPage("we-monitor-kimi") },
  { label: "文心一言监测", value: monitorFaqPage("we-monitor-ernie") },
  { label: "代理商", value: teamSolutionFaqPage("agencies") },
  { label: "大型企业", value: teamSolutionFaqPage("enterprise") },
  { label: "公关与品牌团队", value: teamSolutionFaqPage("pr-brand-teams") },
  { label: "中小企业 GEO 团队", value: teamSolutionFaqPage("smb-geo-teams") },
  { label: "SEO 专家", value: teamSolutionFaqPage("seo-specialists") },
  { label: "品牌危机管理", value: sceneFaqPage("brand-crisis-management") },
  { label: "竞争定位", value: sceneFaqPage("competitive-positioning") },
  { label: "内容策略", value: sceneFaqPage("content-strategy") },
  { label: "叙事构建", value: sceneFaqPage("narrative-shaping") },
  { label: "产品发布", value: sceneFaqPage("product-launch") },
];

export const FAQ_PAGE_LABEL_BY_VALUE = Object.fromEntries(
  FAQ_PAGE_OPTIONS.map((option) => [option.value, option.label]),
) as Record<FaqPageKey, string>;

/** 官网 FAQ 锚点路径（不含 origin） */
export function faqSitePath(page: FaqPageKey): string {
  if (page === FAQ_PAGE.home) return "/#faq";
  if (page === FAQ_PAGE.pricing) return "/pricing/#faq";
  if (page.startsWith("monitor/")) {
    return `/platform/${page.slice("monitor/".length)}/#faq`;
  }
  if (page.startsWith("solution/")) {
    return `/solution/${page.slice("solution/".length)}/#faq`;
  }
  if (page.startsWith("scene/")) {
    return `/scene/${page.slice("scene/".length)}/#faq`;
  }
  return `/${page}/#faq`;
}
