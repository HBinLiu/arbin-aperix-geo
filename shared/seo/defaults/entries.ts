import { CORE_PAGE_SEO } from "./core.ts";
import { MONITOR_PAGE_SEO } from "./monitor.ts";
import { PLATFORM_PAGE_SEO } from "./platform.ts";
import { SOLUTION_TEAM_SEO } from "./solution.ts";
import { type CmsPageSeoSeedEntry, toCmsPageSeoSeed } from "./types.ts";

/** Payload seed 写入 `page-seo` collection 的全量默认条目 */
export const defaultPageSeoEntries: CmsPageSeoSeedEntry[] = [
  toCmsPageSeoSeed(CORE_PAGE_SEO.home),
  toCmsPageSeoSeed(CORE_PAGE_SEO.about),
  toCmsPageSeoSeed(CORE_PAGE_SEO.contact),
  toCmsPageSeoSeed(CORE_PAGE_SEO.pricing),
  toCmsPageSeoSeed(CORE_PAGE_SEO.research),
  toCmsPageSeoSeed(CORE_PAGE_SEO.news),
  toCmsPageSeoSeed(CORE_PAGE_SEO.blog),
  toCmsPageSeoSeed(CORE_PAGE_SEO.academy),
  toCmsPageSeoSeed(CORE_PAGE_SEO.changelogs),
  ...Object.values(PLATFORM_PAGE_SEO).map(toCmsPageSeoSeed),
  ...Object.values(SOLUTION_TEAM_SEO).map(toCmsPageSeoSeed),
  ...Object.values(MONITOR_PAGE_SEO).map(toCmsPageSeoSeed),
];
