/** 便捷 barrel；运行时请优先 `@shared/seo/defaults/*` 直链（与 `@shared/faq/pages` 一致） */
export type {
  CmsPageSeoSeedEntry,
  MonitorPageSeoDefault,
  PageSeoDefault,
} from "./defaults/types";
export { CORE_PAGE_SEO } from "./defaults/core";
export { MONITOR_PAGE_SEO } from "./defaults/monitor";
export { PLATFORM_PAGE_SEO } from "./defaults/platform";
export { SCENE_PAGE_SEO } from "./defaults/scene";
export { SOLUTION_TEAM_SEO } from "./defaults/solution";
export { defaultPageSeoEntries } from "./defaults/entries";
export {
  SITE_NAME_PLACEHOLDER,
  cmsPageSeoTitle,
  toCmsPageSeoSeed,
} from "./defaults/types";
