/** 便捷 barrel；运行时请优先 `@shared/seo/defaults` 直链（与 `@shared/faq/pages` 一致） */
export type {
  CmsPageSeoSeedEntry,
  MonitorPageSeoDefault,
  PageSeoDefault,
} from "./defaults";
export {
  CORE_PAGE_SEO,
  MONITOR_PAGE_SEO,
  PLATFORM_PAGE_SEO,
  SITE_NAME_PLACEHOLDER,
  cmsPageSeoTitle,
  defaultPageSeoEntries,
  toCmsPageSeoSeed,
} from "./defaults";
