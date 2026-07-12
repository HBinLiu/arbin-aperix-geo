import { CORE_PAGE_SEO } from "./core";
import { MONITOR_PAGE_SEO } from "./monitor";
import { PLATFORM_PAGE_SEO } from "./platform";
import { SOLUTION_TEAM_SEO } from "./solution";
import { type CmsPageSeoSeedEntry, toCmsPageSeoSeed } from "./types";

/** Payload seed 写入 `page-seo` collection 的全量默认条目 */
export const defaultPageSeoEntries: CmsPageSeoSeedEntry[] = [
  toCmsPageSeoSeed(CORE_PAGE_SEO.home),
  toCmsPageSeoSeed(CORE_PAGE_SEO.about),
  toCmsPageSeoSeed(CORE_PAGE_SEO.contact),
  toCmsPageSeoSeed(CORE_PAGE_SEO.pricing),
  toCmsPageSeoSeed(CORE_PAGE_SEO.research),
  ...Object.values(PLATFORM_PAGE_SEO).map(toCmsPageSeoSeed),
  ...Object.values(SOLUTION_TEAM_SEO).map(toCmsPageSeoSeed),
  ...Object.values(MONITOR_PAGE_SEO).map(toCmsPageSeoSeed),
];
