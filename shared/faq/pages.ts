/** FAQ `page` 字段取值（Payload 与 website 共用） */

export const FAQ_PAGE = {
  home: "home",
  pricing: "pricing",
  platformAnswer: "platform/answer-engine-insights",
  platformTopics: "platform/find-topics-ideas",
  platformPrompt: "platform/prompt-volumes-explorer",
  platformContent: "platform/content-creation-optimization",
} as const;

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
export type FaqPageKey = (typeof FAQ_PAGE)[keyof typeof FAQ_PAGE] | MonitorFaqPageKey;

export function monitorFaqPage(slug: MonitorFaqSlug): MonitorFaqPageKey {
  return `monitor/${slug}`;
}

export const FAQ_PAGE_OPTIONS = [
  { label: "首页", value: FAQ_PAGE.home },
  { label: "定价", value: FAQ_PAGE.pricing },
  { label: "回答引擎洞察", value: FAQ_PAGE.platformAnswer },
  { label: "发现机会与差距", value: FAQ_PAGE.platformTopics },
  { label: "提示词查询探索", value: FAQ_PAGE.platformPrompt },
  { label: "内容创作与优化", value: FAQ_PAGE.platformContent },
  { label: "豆包监测", value: monitorFaqPage("we-monitor-doubao") },
  { label: "DeepSeek 监测", value: monitorFaqPage("we-monitor-deepseek") },
  { label: "通义千问监测", value: monitorFaqPage("we-monitor-qwen") },
  { label: "腾讯元宝监测", value: monitorFaqPage("we-monitor-yuanbao") },
  { label: "Kimi 监测", value: monitorFaqPage("we-monitor-kimi") },
  { label: "文心一言监测", value: monitorFaqPage("we-monitor-ernie") },
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
  return `/${page}/#faq`;
}
